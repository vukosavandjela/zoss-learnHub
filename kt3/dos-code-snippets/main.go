package main

import (
	"fmt"
	"log"
	"net"
	"net/http"
	"runtime"
	"sync/atomic"
	"time"
)

var activeConnections int64

func main() {
	http.HandleFunc("/api/video/authorize", handleVideoAuthorize)
	http.HandleFunc("/stats", handleStats) // Novi endpoint

	// Ispisuj stats svake 5 sekundi
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			conns := atomic.LoadInt64(&activeConnections)
			goroutines := runtime.NumGoroutine()
			log.Printf("Active connections: %d | Goroutines: %d", conns, goroutines)
		}
	}()

	server := &http.Server{
		Addr: ":8080",
		ConnState: func(conn net.Conn, state http.ConnState) {
			// Prati connection state changes
			switch state {
			case http.StateNew:
				atomic.AddInt64(&activeConnections, 1)
			case http.StateClosed:
				atomic.AddInt64(&activeConnections, -1)
			}
		},
	}

	log.Println("Vulnerable server starting on :8080")
	log.Fatal(server.ListenAndServe())
}

func handleVideoAuthorize(w http.ResponseWriter, r *http.Request) {
	time.Sleep(50 * time.Millisecond)
	fmt.Fprintf(w, `{"status":"authorized","presigned_url":"https://minio.example.com/video/123?token=xyz"}`)
}

func handleStats(w http.ResponseWriter, r *http.Request) {
	conns := atomic.LoadInt64(&activeConnections)
	goroutines := runtime.NumGoroutine()

	fmt.Fprintf(w, `{"active_connections": %d, "goroutines": %d}`, conns, goroutines)
}
