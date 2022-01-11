# vkUploaderEX
Перезапуск python-vkUploader с использованием многопоточности и GUI

## Использование
> ### **Внимание!**
> Для работы приложения необходимо получить файл gdrive_secrets.json для доступа к сервисам Google Cloud! \
> Для этого необходимо:
> 1. Перейти в [Google API Console](https://console.developers.google.com/iam-admin/projects)
> 2. Создать новый проект, если его нет, либо выбрать уже существующий
> 3. В боковом меню найти пункт **_APIs & Services_**, в открывающемся подменю выбрать **_Library_**
> 4. Поочередно найти и включить следующие API:
>    + Google Drive API
>    + Google Sheets API
> 5. В боковом меню в пункте **_APIs & Services_** выбрать **_OAuth consent screen_**, выполнить настройку:
>    1. Ввести название приложения (App name), указать адрес почты поддержки, можно свой (User support email и Developer contact information), продолжить (Save and Continue)
>    2. Добавить области доступа приложения (Add or Remove Scopes), после чего продолжить (Save and Continue):
>       1. Google Drive API (auth/docs)
>       2. Google Sheets API (auth/spreadsheets)
>    3. Добавить тестовых пользователей (Add Users) для того, чтобы они имели доступ к приложению (себя обязательно!), после чего продолжить (Save and Continue)
>    4. Проверить верность введеных данных
> 6. В боковом меню выбрать **_Credentials_**
> 7. Нажать кнопку **_Create credentials_**, в выпавшем меню выбрать **_OAuth client ID_**
> 8. Установить тип приложения (Application type) на Web application
> 9. Ввести название клиента (Name), добавить адрес переадресации (Authorized redirect URIs): `http://localhost:8080/`, сохранить (Create)
> 10. После сохранения в открывшемся окне нажать Download JSON, скачанный файл переместить в папку `<папка приложения>/.config/` с именем `gdrive_secrets.json`
> 11. При первом запуске приложения и выборе Google Sheets как источника данных будет открыто окно браузера с запросом на доступ к данным в Google Drive, настроенное на шаге 5
> 