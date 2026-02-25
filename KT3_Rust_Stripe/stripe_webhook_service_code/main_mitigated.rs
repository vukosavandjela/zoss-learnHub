use axum::{
    Json, Router,
    routing::post,
    http::{StatusCode, HeaderMap},
    body::Bytes,
};
use serde::{Deserialize, Serialize};
use tokio::net::TcpListener;


#[derive(Debug, Deserialize)]
struct WebhookEvent {
    #[serde(rename = "type")]
    event_type: String,
    data: WebhookData,
}

#[derive(Debug, Deserialize)]
struct WebhookData {
    object: PaymentObject,
}

#[derive(Debug, Deserialize)]
struct PaymentObject {
    id: String,
    amount: Option<u64>,
    metadata: Option<CourseMetadata>,
}

#[derive(Debug, Deserialize)]
struct CourseMetadata {
    course_id: Option<String>,
    user_id: Option<String>,
}



fn verify_stripe_signature(
    payload: &[u8],
    signature_header: &str,
    secret: &str,
) -> Result<(), String> {
    use std::collections::HashMap;

    // Parsiranje Stripe-Signature headera
    // Format: t=1614556800,v1=abc123...
    let parts: HashMap<&str, &str> = signature_header
        .split(',')
        .filter_map(|part| {
            let mut kv = part.splitn(2, '=');
            Some((kv.next()?, kv.next()?))
        })
        .collect();

    let timestamp = parts
        .get("t")
        .ok_or("Missing timestamp in Stripe-Signature")?;

    let expected_signature = parts
        .get("v1")
        .ok_or("Missing v1 signature in Stripe-Signature")?;

    // MITIGACIJA: provjera timestamp-a
    // Stripe default tolerancija je 5 minuta (300 sekundi)
    // Štiti od replay napada — stari potpisi se odbijaju
    let ts: i64 = timestamp
        .parse()
        .map_err(|_| "Invalid timestamp format")?;

    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64;

    if (now - ts).abs() > 300 {
        return Err(format!(
            "Timestamp {} is outside tolerance window — possible replay attack",
            timestamp
        ));
    }

    // MITIGACIJA: rekonstrukcija i verifikacija HMAC potpisa
    // Stripe format za signed payload: "timestamp.raw_body"
    let signed_payload = format!(
        "{}.{}",
        timestamp,
        String::from_utf8_lossy(payload)
    );

    use hmac::{Hmac, Mac};
    use sha2::Sha256;
    type HmacSha256 = Hmac<Sha256>;

    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|_| "Invalid webhook secret")?;
    mac.update(signed_payload.as_bytes());
    let computed_signature = hex::encode(mac.finalize().into_bytes());

    // Poređenje računatog i očekivanog potpisa
    if computed_signature != *expected_signature {
        return Err("Signature mismatch — request did not originate from Stripe".to_string());
    }

    Ok(())
}


async fn webhook_handler(
    headers: HeaderMap,
    body: Bytes,
) -> (StatusCode, Json<serde_json::Value>) {

    // MITIGACIJA korak 1: Stripe-Signature header mora postojati
    let stripe_signature = match headers
        .get("Stripe-Signature")
        .and_then(|v| v.to_str().ok())
    {
        Some(sig) => sig.to_string(),
        None => {
            println!("[WEBHOOK] Rejected: Missing Stripe-Signature header");
            return (
                StatusCode::UNAUTHORIZED,
                Json(serde_json::json!({
                    "error": "Unauthorized",
                    "message": "Missing Stripe-Signature header — request rejected"
                })),
            );
        }
    };

    // MITIGACIJA korak 2: webhook secret iz environment varijable
    // Secret se NIKADA ne hardkodira u kod
    let webhook_secret = match std::env::var("STRIPE_WEBHOOK_SECRET") {
        Ok(s) => s,
        Err(_) => {
            println!("[WEBHOOK] Error: STRIPE_WEBHOOK_SECRET not configured");
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(serde_json::json!({
                    "error": "Server configuration error"
                })),
            );
        }
    };

    // MITIGACIJA korak 3: HMAC-SHA256 verifikacija
    // Uključuje timestamp provjeru (anti-replay, 5min tolerancija)
    if let Err(reason) = verify_stripe_signature(&body, &stripe_signature, &webhook_secret) {
        println!("[WEBHOOK] Rejected: {}", reason);
        return (
            StatusCode::UNAUTHORIZED,
            Json(serde_json::json!({
                "error": "Unauthorized",
                "message": format!("Signature verification failed: {}", reason)
            })),
        );
    }

    // Potpis je validan — request je autentifikovan kao Stripe
    println!("[WEBHOOK] Signature verified — processing event");

    let event: WebhookEvent = match serde_json::from_slice(&body) {
        Ok(e) => e,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({
                    "error": format!("Invalid JSON: {}", e)
                })),
            );
        }
    };

    if event.event_type == "payment_intent.succeeded" {
        let course_id = event.data.object.metadata
            .as_ref()
            .and_then(|m| m.course_id.as_deref())
            .unwrap_or("unknown")
            .to_string();

        let user_id = event.data.object.metadata
            .as_ref()
            .and_then(|m| m.user_id.as_deref())
            .unwrap_or("unknown")
            .to_string();

        println!(
            "[WEBHOOK] Course '{}' activated for user '{}' — payment_id: {}",
            course_id, user_id, event.data.object.id
        );

        return (
            StatusCode::OK,
            Json(serde_json::json!({
                "status": "course_activated",
                "course_id": course_id,
                "user_id": user_id,
                "payment_id": event.data.object.id,
                "amount_cents": event.data.object.amount,
                "message": format!(
                    "Course '{}' successfully activated for user '{}'",
                    course_id, user_id
                )
            })),
        );
    }

    (
        StatusCode::OK,
        Json(serde_json::json!({
            "status": "event_ignored",
            "event_type": event.event_type
        })),
    )
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/webhook", post(webhook_handler));

    let listener = TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("=================================================");
    println!(" LearnHub Payment Service — MITIGATED VERSION   ");
    println!("=================================================");
    println!(" POST /webhook  [HMAC-SHA256 VERIFICATION ON]   ");
    println!("=================================================");
    axum::serve(listener, app).await.unwrap();
}

