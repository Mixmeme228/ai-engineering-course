# Ключи и статус доступа

Оба ключа уже настроены локально с подтверждением пользователя. GigaChat работает. HuggingFace отвечает 402 из-за баланса $0.00; пользователь выбрал не пополнять счёт. Ниже сохранена инструкция для последующего повторения настройки.

## GigaChat

1. Откройте [кабинет Studio](https://developers.sber.ru/studio/workspaces/my-space/get/gigachat-api) и войдите самостоятельно по номеру телефона или Сбер ID.
2. Создайте проект GigaChat API. Ознакомьтесь с условиями сервиса перед принятием.
3. В проекте найдите «Настройки API» → «Получить ключ».
4. Сохраните **Authorization key** в поле `GIGACHAT_CREDENTIALS` локального `.env`. Это не временный Access token.
5. Для физического лица scope обычно `GIGACHAT_API_PERS`; сверяйте его со значением в кабинете.

Ключ отображается один раз. Не отправляйте его в чат, комментарии GetCourse, репозиторий и скриншоты.

Основание: [регистрация и проект](https://developers.sber.ru/docs/ru/gigachat/quickstart/ind-create-project), [получение Authorization key](https://developers.sber.ru/docs/ru/gigachain/tools/js/gigachat).

## HuggingFace

1. Войдите или зарегистрируйтесь на [HuggingFace](https://huggingface.co/login).
2. Откройте [создание токена с разрешением Inference Providers](https://huggingface.co/settings/tokens/new?ownUserPermissions=inference.serverless.write&tokenType=fineGrained).
3. Тип **fine-grained**, название `ai-engineering-course`, право **Make calls to Inference Providers**.
4. Создайте токен самостоятельно и вставьте его в `HF_API_KEY` локального `.env`.
5. Ключ не гарантирует доступность конкретной модели и оплату запросов. Если сервис просит оплату, сначала проверьте условия; платные пакеты автоматически не подключались.

Основание: [официальная инструкция Inference Providers](https://huggingface.co/docs/inference-providers/index#authentication).

## Когда готово

В `.env` должны быть непустыми `GIGACHAT_CREDENTIALS` и `HF_API_KEY`. После этого можно выполнить реальные эксперименты и завершить сдачу. Сам файл остаётся локальным и исключён из Git и передаваемого архива.
