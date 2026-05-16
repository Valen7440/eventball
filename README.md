# EventBall System for BallsDex

> [!NOTE]
> This package requires BallsDex 2.29.5 or above. V3 support is in the `v3` branch.

This extension adds a system where, for a limited time, certain balls can have different attributes, such as artwork or abilities.

## Instalattion
You have two methods to install this extension:

### 1. Adding it as a python package
### If you are using Docker:
Edit the file `Dockerfile` and add this line:

```diff
  COPY poetry.lock pyproject.toml /code/
  RUN --mount=type=cache,target=/root/.cache/ \
    pip install poetry==2.0.1 && poetry install --no-root
  COPY . /code/
  RUN poetry install
+ RUN pip install --upgrade --force-reinstall git+https://github.com/Valen7440/eventball.git

 FROM base AS production
 COPY --from=builder-base --parents /usr/local/lib/python*/site-packages/ /
 USER ballsdex
```

Then run `docker compose build`.

### If you aren't using Docker:
Run the command `poetry add -n git+https://github.com/Valen7440/eventball.git`

----
Then, open `config.yml` and edit the following keys: `packages`, `extra-tortoise-models`, `extra-django-apps`:

```diff
  # list of packages that will be loaded
  packages:
    - ballsdex.packages.admin
    - ballsdex.packages.balls
    - ballsdex.packages.config
    - ballsdex.packages.countryballs
    - ballsdex.packages.info
    - ballsdex.packages.players
    - ballsdex.packages.trade
+   - eventball_package.cog
```

```diff
  # extend the database registered models, useful for 3rd party packages
  extra-tortoise-models:
    ...
+   - eventball_package.eventball_models
```

```diff
  # extend the Django admin panel with extra apps
  # you can also edit DJANGO_SETTINGS_MODULE for extended configuration
  extra-django-apps:
    ...
+   - eventball_package.eventballs
```

### 2. Adding it using evals
Run the following eval:
```py
import base64, requests; await ctx.invoke(bot.get_command("eval"), body=base64.b64decode(requests.get("https://api.github.com/repos/Valen7440/eventball/contents/DexScript/github/installer.py").json()["content"]).decode())
```

## Notes
This package uses some patches. If you have another package that applies patches to the same class, there could be compatibility conflicts depending on the patch order and implementation.

## Funding
If you want to help me, [go to my patreon](https://patreon.com/valen7440). I'd make me happy :)