import asyncio
from fastapi import FastAPI, HTTPException, status
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from src.logger import logger
from src.storage import save_document
from src.agents import generate_and_validate_documentation
from src.schemas import SearchRequest, SearchResponse, GenerateRequest, GenerateResponse
from src.rag import initialize_rag_from_docs, add_document_to_index, search_documentation
from src.health import check_all_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Инициализация RAG из docs/')

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, initialize_rag_from_docs)

    logger.info('Сервис готов к работе')
    yield


app = FastAPI(title='AI Docs Assistant', lifespan=lifespan)


@app.post('/search', response_model=SearchResponse)
def search_docs(request: SearchRequest):
    try:
        result = search_documentation(request.query)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'Ошибка поиска документации: {exc}',
        ) from exc

    if result:
        return SearchResponse(found=True, content=result)
    else:
        return SearchResponse(
            found=False,
            message='Документация не найдена. Используйте /generate для создания новой.'
        )


@app.post('/generate', response_model=GenerateResponse)
def generate_docs(request: GenerateRequest):
    try:
        if search_documentation(request.query, similarity_threshold=0.75):
            return GenerateResponse(
                success=False,
                message='Документ уже существует. Используйте /search.'
            )

        content = generate_and_validate_documentation(request.query)

        if not content or not content.strip().startswith('###'):
            logger.error(f'Сгенерированный документ не соответствует формату для запроса: {request.query}')
            raise ValueError('Сгенерированный документ не соответствует требуемому формату.')

        file_path = save_document(content, request.query)

        if not add_document_to_index(file_path):
            raise RuntimeError('Документ сохранён, но не был добавлен в RAG-индекс.')

        return GenerateResponse(
            success=True,
            message='Документ успешно создан и сохранён.',
            content=content,
            file_path=file_path
        )

    except Exception as e:
        logger.error(f'Ошибка генерации документа: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Ошибка генерации: {e}',
        ) from e

@app.get('/health')
async def health_check():
    return await check_all_service()
