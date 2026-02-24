package main

import (
	"fmt"
	"log"
	"net/http"
	"time"
)

func main() {
	http.HandleFunc("/api/video/authorize", handleVideoAuthorize)

	server := &http.Server{
		Addr:         ":8080",
		ReadTimeout:  5 * time.Second,   // MITIGACIJA
		WriteTimeout: 10 * time.Second,  // MITIGACIJA
		IdleTimeout:  120 * time.Second, // MITIGACIJA
	}

	log.Println("Patched server starting on :8080 with timeouts")
	log.Printf("ReadTimeout: %v, WriteTimeout: %v, IdleTimeout: %v",
		server.ReadTimeout, server.WriteTimeout, server.IdleTimeout)
	log.Fatal(server.ListenAndServe())
}

func handleVideoAuthorize(w http.ResponseWriter, r *http.Request) {
	time.Sleep(50 * time.Millisecond)
	fmt.Fprintf(w, `{"status":"authorized","presigned_url":"https://minio.example.com/video/123?token=xyz"}`)
}
