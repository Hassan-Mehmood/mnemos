# Frontend Authentication API Integration Documentation

## Base URL

Ensure you append these endpoints to your backend base URL (e.g.,
`http://localhost:8000/api/v1`).

### 1. Register (Sign Up)

**POST** `/auth/register`

- **Description:** Registers a new user account.
- **Request Body (JSON):**

    ```json
    {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "password": "your_secure_password"
    }
    ```

- **Successful Response (200 OK):**
    ```json
    {
        "success": true,
        "data": {
            "id": "e6bd35a2-9b25-4c6e-8d8a-1a8c88c7c72f",
            "name": "John Doe",
            "email": "john.doe@example.com"
        },
        "message": "Success"
    }
    ```
- **Error Responses:**
    - `400 Bad Request`: If the email is already registered.

### 2. Login (Sign In)

**POST** `/auth/login`

- **Description:** Authenticates a user and returns a JWT token.
- **Request Body (JSON):**

    ```json
    {
        "email": "john.doe@example.com",
        "password": "your_secure_password"
    }
    ```

- **Successful Response (200 OK):**
    ```json
    {
        "success": true,
        "data": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer"
        },
        "message": "Success"
    }
    ```
- **Error Responses:**
    - `401 Unauthorized`: Returns "Invalid credentials" if the email/password
      combination is wrong.

### Using the JWT Token

Once you receive the `access_token` from the login endpoint, store it securely
(e.g., `localStorage`, `sessionStorage`, or an HTTP-first cookie strategy
whichever you prefer).

Attach it to every subsequent protected API request in the `Authorization`
header:

- `Authorization: Bearer <your_access_token>`
