# <img src="https://github.com/davidmrtns/replyai-frontend/blob/main/src/replyai-logo.svg?raw=true" width="28px" /> ReplyAI (API)

![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue&style=for-the-badge)
![FastAPI](https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=FASTAPI&logoColor=white&style=for-the-badge)

## Project Description
ReplyAI is a backend application developed with FastAPI, designed to act as a bridge between artificial intelligence assistants and a WhatsApp number. Its operation is based on a request-and-response architecture: when receiving a message from a customer, the system triggers an endpoint that processes the content with an AI (OpenAI in this project), which not only generates a natural-language response but is also capable of **executing automated routines** according to the conversation context.

This includes actions such as checking or scheduling appointments, sending images or videos, retrieving information from external systems, starting custom support flows, and much more. It is ideal for support systems, advanced chatbots, or any application that requires intelligent responses combined with automated task execution.

## Features
- 💬 **AI-generated responses**: automatically responds to messages received via WhatsApp using natural-language models;
- 🖼️ **Media sending**: in addition to text messages, the API can send pre-registered images, videos, and documents, as well as respond with audio when it receives a voice message;
- 📅 **Scheduling**: the API integrates with Outlook and Google Calendar to create appointments, check available time slots, and suggest them to customers;
- 💸 **Billing management**: automated delivery of billing messages to delinquent customers;
- ⏰ **Due-date reminders**: automatically notifies customers about installments that are nearing their due dates through its Asaas integration.
- 🙏 **Thank-you messages**: sends automatic thank-you messages after boleto payments.
- 📄 **Invoice sending**: forwards invoices issued through Asaas directly to the customer;
- 🤖 **Application management**: the API provides endpoints for fully managing the tool's operation.

### Integrations
| Category                   | Tools/Services                                | Purpose                                                      |
|----------------------------|----------------------------------------------|---------------------------------------------------------------|
| 📅 **Virtual calendars**   | Google Calendar, Outlook                     | Automated appointment scheduling                              |
| 💬 **WhatsApp API**        | Digisac, EvolutionAPI                        | Sending and receiving messages                                |
| 📊 **CRM**                 | RD Station CRM                               | Lead registration and management                              |
| 🤖 **Response generation** | OpenAI (Responses API)                       | Intelligent response generation                               |
| 🔉 **Audio responses**     | ElevenLabs                                   | Converting text to natural audio                              |
| ☁️ **Storage**             | Azure Blob Storage                           | Storing images, videos, and other generated files             |

## Development
### Configure and Run the Containers
1. Make sure Docker Desktop and Docker Compose are installed and running.
2. Create the environment file from the example:

    ```bash
    cp .env.example .env
    ```

    On Windows PowerShell, use:

    ```powershell
    Copy-Item .env.example .env
    ```

3. Update `.env` with the credentials and integration settings required for your environment. 
    > _For local development, the database and Redis hostnames must remain `db` and `redis`, respectively, because these are the service names on the Docker network._

4. Build and start all containers in the background:

    ```bash
    docker compose up --build -d
    ```

The stack includes PostgreSQL (`db`), Redis (`redis`), Evolution API (`evolution-api`), the FastAPI application (`replyai-api`), and the background worker (`replyai-worker`).

**Useful commands:**

```bash
# Show container status
docker compose ps

# Follow logs for the whole stack or for one service
docker compose logs -f
docker compose logs -f replyai-api
docker compose logs -f replyai-worker

# Stop and remove the containers and network
docker compose down

# Stop the containers and remove their persistent volumes
docker compose down -v
```

### Test the Container Connections
Run these commands from the project directory after starting the stack:

```bash
# Check PostgreSQL readiness
docker compose exec db pg_isready -U postgres -d postgres

# Check Redis connectivity
docker compose exec redis redis-cli ping

# Check that the API is reachable from the host
curl http://localhost:8000/

# Check that the API container can reach the database and Redis services
docker compose exec replyai-api python -c "import socket; socket.create_connection(('db', 5432), 5).close(); socket.create_connection(('redis', 6379), 5).close(); print('db: connected'); print('redis: connected')"
```

The expected responses are:
- `accepting connections` from PostgreSQL;
- `PONG` from Redis; and
- `{"status":"The API is running"}` from the API.

If a service is not ready, inspect its output with `docker compose logs <service-name>` and confirm that all required values in `.env` are configured.

### Technologies Used
- **Backend**: FastAPI;
- **Database ORM**: SQLAlchemy.

## Author
- David Martins - [@davidmrtns](https://github.com/davidmrtns/)
