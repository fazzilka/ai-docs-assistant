import re

from crewai import Agent, Task, Crew, LLM

from src.logger import logger
from src.settings import settings


llm = LLM(
    model=settings.OLLAMA_MODEL,
    api_base=settings.OLLAMA_API_BASE,
    temperature=0.0,
    timeout=60.0,
    max_tokens=300,
    api_key=settings.API_KEY
)


def _create_generator_agent():
    return Agent(
        role='API-документатор',
        goal='Генерировать документацию в строгом формате.',
        backstory=(
            'Ты специалист по REST API. Генерируй документацию ТОЛЬКО в формате:\n'
            '### <HTTP-метод> /api/v1/<путь>\n'
            '**Описание**: ... \n'
            '**Параметры**: ... или **Параметры пути**: ... \n'
            '**Ответ**:\n'
            '```json\n{...}\n```\n'
            'В заголовке всегда указывай реальный метод GET, POST, PUT, PATCH или DELETE; '
            'никогда не пиши буквальное слово «МЕТОД». Путь должен начинаться с /api/v1. '
            'Для удаления пользователя по id используй строго этот документ:\n'
            '### DELETE /api/v1/users/{id}\n\n'
            '**Описание**: Удаляет пользователя по его идентификатору.\n\n'
            '**Параметры пути**:\n'
            '- `id` (integer): уникальный идентификатор пользователя\n\n'
            '**Ответ**:\n'
            '```json\n'
            '{"message": "User deleted"}\n'
            '```'
        ),
        llm=llm,
        verbose=False
    )


def _create_validator_agent():
    return Agent(
        role='Валидатор документации',
        goal='Проверять соответствие документа строгому формату.',
        backstory=(
            'Ты строгий QA-инженер. Ты должен проверить, что документ содержит:\n'
            '1. Заголовок с реальным HTTP-методом вида "### DELETE /api/v1/users/{id}",\n'
            '2. Блок "**Описание**:",\n'
            '3. Блок "**Параметры" или "**Параметры пути**:",\n'
            '4. Блок "**Ответ**:" с JSON-примером в тройных кавычках.\n'
            'Слово «МЕТОД» вместо GET/POST/PUT/PATCH/DELETE недопустимо. '
            'Если всё есть — ответь ровно "valid". Иначе — ровно "invalid".'
        ),
        llm=llm,
        verbose=False
    )


def generate_and_validate_documentation(query: str) -> str | None:
    logger.info(f'Запуск генерации по запросу: {query}')

    generator = _create_generator_agent()
    gen_task = Task(
        description=(
            f'Создай документацию для запроса: {query}. '
            'Определи конкретный HTTP-метод и REST-путь. '
            'Не используй слово «МЕТОД» как значение и обязательно начинай путь с /api/v1.'
        ),
        expected_output='Документ в строгом формате. Ничего больше.',
        agent=generator
    )
    gen_crew = Crew(agents=[generator], tasks=[gen_task])
    raw_content = str(gen_crew.kickoff()).strip()

    if not raw_content:
        logger.error(f'Генерация вернула пустой результат для запроса: {query}')
        return None

    if not _has_required_format(raw_content):
        logger.warning(f'Генератор вернул документ неверного формата для запроса: {query}')
        return None

    validator = _create_validator_agent()
    val_task = Task(
        description=f'Проверь документ:\n\n{raw_content}',
        expected_output='Только "valid" или "invalid", без пояснений.',
        agent=validator
    )
    val_crew = Crew(agents=[validator], tasks=[val_task])
    validation_result = str(val_crew.kickoff()).strip().lower()

    if validation_result == 'valid':
        logger.info(f'Документ прошёл валидацию для запроса: {query}')
        return raw_content
    else:
        logger.warning(f'Документ не прошёл валидацию: {validation_result} для запроса: {query}')
        return None


def _has_required_format(content: str) -> bool:
    header_is_valid = re.match(
        r'^### (GET|POST|PUT|PATCH|DELETE) /api/v1/\S+$',
        content.strip().splitlines()[0],
    )
    has_parameters = '**Параметры**:' in content or '**Параметры пути**:' in content
    return bool(
        header_is_valid
        and '**Описание**:' in content
        and has_parameters
        and '**Ответ**:' in content
        and '```json' in content
        and content.rstrip().endswith('```')
    )
