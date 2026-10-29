#!/usr/bin/env python3
"""
Точка входа запуска прототипа «Профессиональный навигатор».
Запускает ASGI сервер на порту 8000.
"""
import uvicorn
from app.config import HOST, PORT
from app.database import init_db

if __name__ == "__main__":
    init_db()
    print("=" * 65)
    print("🚀 Запуск сервиса «Профессиональный навигатор» (Свердловская область)")
    print(f"📡 Сервер доступен по адресу: http://localhost:{PORT}")
    print(f"📱 Интерфейс оптимизирован для мобильных устройств и десктопа")
    print("=" * 65)
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)

