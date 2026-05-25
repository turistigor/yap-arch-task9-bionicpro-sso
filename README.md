# Объединение сервисов через SSO и работа с данными для аналитики

## Задание 1. Повышение безопасности системы

### Задача 1. Предложите архитектурное решение и доработайте диаграмму C4 для управления учётными данными пользователя.

Решение:
- Использовать IAM (Keycloak) с собственным хранилищем для:
    - передачи credentials IdP для аутентификации;
    - реализации workflow работы с токенами (создание, инвалидация, перевыпуск, отзыв);
    - реализации workflow работы с пользовательскими сессиями (создание, завершение).
- Реализовать сервис (auth-service на Python + FastAPI) в качестве точки входа для всех сервисов с запросами аутентификации и авторизации.
- Реализовать интеграцию IAM с региональными системами хранения данных пользователей (Regional IdP):
    - проверка предоставленных учетных данных пользователей;
    - реализация принципа локального хранения данных пользователей;
    - использование существующих систем хранения аутентификационных данных.
- Реализовать session-cache сервис для хранения сессионных данных в течении срока жизни.

![](./arch/c4_containers_to_be.png)

### Задача 2. Улучшите безопасность существующего приложения, заменив Code Grant на PKCE.

Данное задание было выполнено в соответствии с порядковым номером, после чего код был изменен в соответствии с требованиями задания 1.3.
В текущем отчете представлена реализация для двух вариантов хранения токенов: на фронте и на бэке.

#### Использование PKCE при хранении токенов на фронте

Код можно найти в комите [2d67e97](https://github.com/turistigor/yap-arch-task9-bionicpro-sso/pull/1/changes/2d67e9796df9e404a0b6b247f01e80f4035edb95). 

Для включения PKCE были проделаны следующие действия:

- включение для клиента reports-frontend в админке keycloak

![](./pictures/auth_pkce_keycloak_admin_panel.png)

- включение со стороны клиента через параметры ReactKeycloakProvider

[Исходники](./frontend/src/App.tsx)

```ts
const App: React.FC = () => {
  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={{
        onLoad: 'login-required',
        pkceMethod: 'S256'
      }}
    >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};
```

Как запрос аутентификации выглядел до включения PKCE:

![](./pictures/auth_init.png)

Как запрос аутентификации выглядел после включения PKCE:
- отправка code_challenge

![](./pictures/auth_pkce.png)

- отправка code_verifier

![](./pictures/auth_pkce_token.png)

#### Использование PKCE при хранении токенов на бэке

Взаимодействие с Keycloak сосредоточено в сервисе [auth](./auth). С кодом можно ознакомиться в файлах:
- [auth/src/api/auth.py](./auth/src/api/auth.py)
- [auth/src/auth/keycloak.py](./auth/src/auth/keycloak.py)

Более подробное описание содержится в следующем разделе.

### Задача 3. Обеспечьте безопасное получение и хранение access-и refresh-токенов.

Задача реализована в сервисе [auth](./auth)

Для запуска выполнить:
```bash
cp .env.example .env
# edit auth/.env according to the hints inside

docker-compose up -d
```

**Интеграция с Keycloak, перенос работы с токенами и сессиями**

Интеграция реализована при помощи библиотеки [python-keycloak](https://pypi.org/project/python-keycloak/).  

1. Пользовательский запрос на аутентификацию (/login) перенаправляется в Keycloak с:
   - code_challenge и state в query для последующего возврата после успешной аутентификации;
   - code_verifier и state в Secure, HttpOnly cookies (через [starlet.SessionMiddleware](https://starlette.dev/middleware/#sessionmiddleware)), зашифрованные при помощи SESSION_SECRET_KEY как эталонные значения для проверки в /callback после успешной аутентификации (cookie session в Response headers).

![](./pictures/auth_back_login.png)

2. Пользователь получает и заполняет форму аутентификации, после чего отправляет её в Keycloak.

3. Успешная аутентификация перенаправляется в /callback с ранее переданными state и полученным от Keycloak code:
  - сервис проверяет совпадение state из query со state из cookie;
  - сервис отправляет запрос в Keycloak для получения токенов в обмен на code (из query) и code_verifier (из cookie);
  - создается сессия (с сохранением в Redis), содержащая токены и информацию о них;
  - фронтенду возвращается session_id (Secure, HttpOnly cookie) и презентационные сведения о пользователе (имена, почта и т.д.).

![](./pictures/auth_back_login_callback.png)

4. Фронтенд отображает интерфейс аутентифицированного пользователя.

![](./pictures/auth_back_login_success.png)


Диаграмма последовательно реализованного процесса аутентификации.

![](./pictures/auth_back_pkce_sequence.png)


**Workflow токенов**

После получения в сервисе auth токены хранятся в зашифрованном виде в Redis. Ключ шифрования задается как env-переменная TOKEN_ENCRYPT_KEY. Связь между токенами и сессией обеспечивается за счет того, что session_id является ключом в Redis, а токены сохранены в значении для этого ключа. Пользователю отдается session_id (HttpOnly, Secure cookie), генерируемое при каждой успешной аутентификации.

Обновление access_token-а осуществляется автоматически при проверке статуса (/status) или обращении другого сервиса за авторизацией (/me). В случае устаревания refresh_token сессия считается завершенной, требуется повторная аутентификация.

TTL: 
- для access_token-а установлено в [realm-export.json](keycloak/realm-export.json) (accessTokenLifespan).
- для refresh_token (всей сессии) по умолчанию составляет 10 часов (или 30 минут в случае простоя) (В интерфейсе: Realm settings -> Sessions -> SSO Session Idle / SSO Session Max).

Ротация session_id осуществляется при смене access_token-а. TTL access_token мало, потому ротацию с таким таймаутом считаю достаточной для защиты от session fixation attack.

Замены access_token и session_id происходят без участия пользователя.

### Задача 4. Добавьте LDAP для возможности получения данных о пользователях представительства BionicPRO в другой стране.

Настройка интеграции и mapping ролей произведены через web-интерфейс Keycloak.

Проведенная настройка для интеграции Keycloak c LDAP показана на скринах:

![](./pictures/keycloak-ldap-conection.png)

![](./pictures/keycloak-ldap-conection2.png)

Так как имена ролдей в LDAP и Keycloak имеют одинаковое написание, выбран role-ldap-mapper.  
Настройки на скрине ниже:

![](./pictures/keycloak-ldap-roles-mapping.png)

Результат содержится в экспортированном [keycloak-results-export.json](keycloak/keycloak-results-export.json).


#### Задача 5. Настройте MFA.

Настройка через web-интерфейс Keycloak представлена на скринах.


Authentication -> Flows (tab) -> browser

![](pictures/keycloak-otp.png)

Authentication -> Required actions

![](pictures/keycloak-otp2.png)

Результат содержится в экспортированном [keycloak-results-export.json](keycloak/keycloak-results-export.json).