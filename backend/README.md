# Backend Pica Ponto

Backend Django com autenticação por sessão. Trabalhadores iniciam e param períodos de trabalho; employers consultam apenas os trabalhadores associados; administradores consultam todos os períodos na API e em `/admin/`.

## Arranque local

```sh
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cd picaponto
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Criar employers e trabalhadores em `/admin/`. Para cada trabalhador, preencher `employer`. Os utilizadores devem ter um `username` e uma palavra-passe. Migrações são versionadas; `db.sqlite3` é local.

## API

Todos os endpoints devolvem JSON. Usar cookies de sessão e enviar o cabeçalho `X-CSRFToken` nas chamadas POST. Obter primeiro `GET /api/auth/csrf/`; o cookie `csrftoken` contém o valor do cabeçalho. O frontend deve usar a mesma origem ou um proxy para `/api/`.

| Método | Endpoint | Acesso | Resultado |
| --- | --- | --- | --- |
| GET | `/api/auth/csrf/` | Público | Define o cookie CSRF |
| POST | `/api/auth/login/` | Público | JSON `{"username":"...","password":"..."}`; cria sessão |
| POST | `/api/auth/logout/` | Autenticado | Termina sessão |
| GET | `/api/auth/me/` | Autenticado | Utilizador atual |
| GET | `/api/auth/workers/` | Employer/admin | Trabalhadores visíveis |
| POST | `/api/entries/start/` | Trabalhador | Inicia um período; `409` se já houver um aberto |
| POST | `/api/entries/stop/` | Trabalhador | Termina o período aberto; `409` se não houver nenhum |
| GET | `/api/entries/` | Autenticado | Períodos visíveis no dia ou semana |
| GET | `/api/reports/` | Autenticado | Segundos trabalhados por trabalhador e por dia |

`entries` e `reports` aceitam `period=day|week` (por omissão `day`), `date=YYYY-MM-DD` (por omissão hoje em Lisboa) e `worker_id` para filtrar um trabalhador autorizado. Uma semana começa na segunda-feira. Os períodos que atravessam a meia-noite são divididos pelos dias locais; os períodos abertos contam até ao momento da consulta. O admin vê todos os trabalhadores, o employer apenas os seus, e o trabalhador apenas os próprios dados.

Para produção, definir `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` conforme [`.env.example`](.env.example). Servir por HTTPS. O backend usa SQLite por omissão.

## Verificações

```sh
cd backend/picaponto
python manage.py test
python manage.py check
```
