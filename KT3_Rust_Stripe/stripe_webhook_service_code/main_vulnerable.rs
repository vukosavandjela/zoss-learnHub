use axum::{
    Json, Router,
    routing::post,
    http::StatusCode,
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

#[derive(Serialize)]
struct WebhookResponse {
    status: String,
    message: String,
    course_id: String,
    user_id: String,
}

async fn webhook_handler(
    body: Bytes,
) -> (StatusCode, Json<WebhookResponse>) {

    // RANJIVOST: Stripe-Signature header se ne čita niti verificira
    // Aplikacija ne zna da li request dolazi od Stripea ili napadača

    let event: WebhookEvent = match serde_json::from_slice(&body) {
        Ok(e) => e,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(WebhookResponse {
                    status: "error".to_string(),
                    message: format!("Invalid JSON: {}", e),
                    course_id: "unknown".to_string(),
                    user_id: "unknown".to_string(),
                }),
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

        // U realnom sistemu ovdje bi bio poziv baze podataka:
        // db::activate_course_access(&user_id, &course_id).await;
        println!(
            "[WEBHOOK]  Course '{}' activated for user '{}' — payment_id: {}",
            course_id, user_id, event.data.object.id
        );

        return (
            StatusCode::OK,
            Json(WebhookResponse {
                status: "course_activated".to_string(),
                message: format!("Course '{}' successfully activated for user '{}'", course_id, user_id),
                course_id,
                user_id,
            }),
        );
    }

    (
        StatusCode::OK,
        Json(WebhookResponse {
            status: "event_ignored".to_string(),
            message: format!("Event '{}' ignored", event.event_type),
            course_id: "unknown".to_string(),
            user_id: "unknown".to_string(),
        }),
    )
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/webhook", post(webhook_handler));

    let listener = TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("=================================================");
    println!(" LearnHub Payment Service — VULNERABLE VERSION  ");
    println!("=================================================");
    println!(" POST /webhook  [NO SIGNATURE VERIFICATION]     ");
    println!("=================================================");
    axum::serve(listener, app).await.unwrap();
}
