use axum::{Json, Router, routing::post, http::StatusCode};
use serde::{Deserialize, Serialize};
use tokio::net::TcpListener;

#[derive(Deserialize)]
struct CheckoutRequest {
    item_price: u32,
    quantity: u32,
}

#[derive(Serialize)]
struct CheckoutResponse {
    total_charged: u32,
    stripe_payment_intent: String,
    message: String,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

async fn checkout(
    Json(payload): Json<CheckoutRequest>,
) -> Result<Json<CheckoutResponse>, (StatusCode, Json<ErrorResponse>)> {

    // MITIGACIJA: checked_mul umjesto direktnog * operatora
    // Ako overflow nastane → vraća None
    // None → 400 Bad Request, Stripe se NIKADA ne poziva
    // Radi ispravno u debug I release modu
    let total = payload.item_price
        .checked_mul(payload.quantity)
        .ok_or_else(|| {
            (
                StatusCode::BAD_REQUEST,
                Json(ErrorResponse {
                    error: format!(
                        "Invalid order: arithmetic overflow detected. \
                         Cannot process {} items at {} cents each.",
                        payload.quantity, payload.item_price
                    ),
                }),
            )
        })?;

    let stripe_intent = format!("pi_simulated_charge_{}_cents", total);

    Ok(Json(CheckoutResponse {
        total_charged: total,
        stripe_payment_intent: stripe_intent,
        message: format!(
            "Successfully charged {} cents for {} items at {} cents each.",
            total, payload.quantity, payload.item_price
        ),
    }))
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/checkout", post(checkout));

    let listener = TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("Payment service running on http://localhost:3000");
    println!("POST /checkout");
    axum::serve(listener, app).await.unwrap();
}
