import uvicorn

from customer.config.config import settings


def main():
    uvicorn.run('customer.api.app:app',
                host=settings.app_host,
                port=settings.app_port)


if __name__ == '__main__':
    main()