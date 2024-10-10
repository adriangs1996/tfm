
package main

import (
    "github.com/labstack/echo/v4"
    "golang.org/x/crypto/bcrypt"
    "net/http"
)

// Simple in-memory store for this example
var users = map[string]string{}

func hashPassword(password string) (string, error) {
    bytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
    return string(bytes), err
}

func checkPasswordHash(password, hash string) bool {
    err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
    return err == nil
}

func register(c echo.Context) error {
    var json struct {
        Username string `json:"username"`
        Password string `json:"password"`
    }

    if err := c.Bind(&json); err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid request"})
    }

    hash, err := hashPassword(json.Password)
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{"error": "Failed to hash password"})
    }

    users[json.Username] = hash
    return c.JSON(http.StatusCreated, map[string]string{"message": "User registered successfully"})
}

func login(c echo.Context) error {
    var json struct {
        Username string `json:"username"`
        Password string `json:"password"`
    }

    if err := c.Bind(&json); err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid request"})
    }

    hash, ok := users[json.Username]
    if !ok || !checkPasswordHash(json.Password, hash) {
        return c.JSON(http.StatusUnauthorized, map[string]string{"error": "Invalid username or password"})
    }

    return c.JSON(http.StatusOK, map[string]string{"message": "Login successful"})
}

func main() {
    e := echo.New()

    e.POST("/register", register)
    e.POST("/login", login)

    e.Start(":8080")
}
