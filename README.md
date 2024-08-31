# FastAPI Application

This is a FastAPI application using PostgreSQL as the database. The application is built with Python 3 and managed with Poetry for dependency management and virtual environments. All services are containerized and managed through Docker Compose.

## Requirements

- **Python 3.x**
- **Poetry**
- **Docker**
- **Docker Compose**

## Installation

1. **Clone the repository**:
   
   ```bash
   git clone https://github.com/AleksSwan/family.git
   cd family
   ```

2. **Set up environment variables**:

   Create a `.env` file in the root directory and set your environment variables as needed (e.g., database URL, secret keys).

## Usage

### Running the Application

The application and its dependencies are managed using Docker Compose. Below are the available Makefile targets to streamline common tasks:

- **`up`**: Start the FastAPI application and related services using Docker Compose.

    ```bash
    make up
    ```

- **`down`**: Stop all services running via Docker Compose.

    ```bash
    make down
    ```

- **`lint`**: Run code linters and checkers within the Docker containers to ensure code quality.

    ```bash
    make lint
    ```

- **`test`**: Execute all tests to verify the application functionality.

    ```bash
    make test
    ```

- **`clean`**: Remove build artifacts and temporary files to maintain a clean working environment.

    ```bash
    make clean
    ```

- **`paths`**: Display the Python paths used by the application.

    ```bash
    make paths
    ```

- **`help`**: Show help information for all available Makefile targets.

    ```bash
    make help
    ```

## Additional Information

- **FastAPI**: This application is built with FastAPI, a modern, fast (high-performance) web framework for building APIs with Python 3. The application includes RESTful endpoints for various operations and utilizes asynchronous capabilities for improved performance.

- **Database**: PostgreSQL is used as the database, and it runs as a Docker service. Ensure your `.env` file correctly specifies the database connection details.


