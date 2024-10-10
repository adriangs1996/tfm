// main.go
package main

import (
    "github.com/gin-gonic/gin"
    "golang.org/x/crypto/bcrypt"
    "net/http"
    "sync"
)

var (
    users = make(map[string]string) // In-memory user store
    mu    sync.Mutex
)

// Handler for user registration
func register(c *gin.Context) {
    var user struct {
        Email    string `json:"email"`
        Password string `json:"password"`
    }

    if err := c.ShouldBindJSON(&user); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    hashedPassword, err := bcrypt.GenerateFromPassword([]byte(user.Password), bcrypt.DefaultCost)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Error hashing password"})
        return
    }

    mu.Lock()
    users[user.Email] = string(hashedPassword)
    mu.Unlock()

    c.JSON(http.StatusCreated, gin.H{"message": "User registered"})
}

// Handler for user login
func login(c *gin.Context) {
    var user struct {
        Email    string `json:"email"`
        Password string `json:"password"`
    }

    if err := c.ShouldBindJSON(&user); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    mu.Lock()
    hashedPassword, exists := users[user.Email]
    mu.Unlock()

    if !exists {
        c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
        return
    }

    err := bcrypt.CompareHashAndPassword([]byte(hashedPassword), []byte(user.Password))
    if err != nil {
        c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid email or password"})
        return
    }

    c.JSON(http.StatusOK, gin.H{"message": "Logged in successfully"})
}

func main() {
    r := gin.Default()

    r.POST("/register", register)
    r.POST("/login", login)

    r.Run(":8080")
}
