use axum::{Json, Router, routing::post};
use serde::{Deserialize, Serialize};
use tokio::net::TcpListener;

#[derive(Deserialize)]
struct CheckoutRequest {
    item_price: u32,  // cijena u centima
    quantity: u32,
}

#[derive(Serialize)]
struct CheckoutResponse {
    total_charged: u32,
    stripe_payment_intent: String,
    message: String,
}

async fn checkout(
    Json(payload): Json<CheckoutRequest>,
) -> Json<CheckoutResponse> {

    let total = payload.item_price * payload.quantity;

    // Simulacija Stripe poziva sa pogrešnim iznosom
    let stripe_intent = format!("pi_simulated_charge_{}_cents", total);

    Json(CheckoutResponse {
        total_charged: total,
        stripe_payment_intent: stripe_intent,
        message: format!(
            "Successfully charged {} cents for {} items at {} cents each.",
            total, payload.quantity, payload.item_price
        ),
    })
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



