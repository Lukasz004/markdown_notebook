# Secure markdown notebook

This web application allows multiple users to store their markdown notes in a secure way.

App was written in **Flask** and uses **Gunicorn** as a HTTP server, **NGINX** as a proxy and **Docker** for containerization.

It provides the following functionality:
- register user with password-strength verification
- logging into account with mandatory using of 2FA
- adding private and not-ciphered markdown note
- deleting user's notes
- displaying sanitized markdown note converted into HTML

**Sanitization in app uses whitelist** and passes only `p`,`h1`--`h6`,`blockquote`,`ul`,`ol`,`li`,`pre`,`hr`,`em`,`strong`,`code`,`a`, `img`, `br` tags and `href`, `title`, `src`, `alt`, `class` attributes.

**App is protected against timing attacks** and **brute-force attacks** due by limiting number of POST queries and using default fake account when user is typing login which does not exist. 
What's more TOTP secret and password are hashed using SHA256 and Argon2ID. Sanitization prevents from **XSS Injection**.

# Launching application

Application needs docker to build a container. 

You need to create the following files:
- self-signed SSL certificate to HTTPS communicaton in `nginx\certs`
- .env file with environmentals variables: `SECRET_KEY`, `DATABASE`, `PEPPER`

Then you can build and run the container using `docker compose up --build`.