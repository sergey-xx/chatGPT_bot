# chatGPT_bot
telegram bot for  openai chatGPT

Стек:
- python 3.9
- openai 0.28.1
- python-telegram-bot 13.7

Запуск проекта в докере:

1. Разместить в папке файл "docker-compose.production.yml".
2. Создать в этой же папке файл .env (см. образец .env.example).
3. Выполнить команду

```bash
sudo docker compose -f docker-compose.production.yml up -d
```