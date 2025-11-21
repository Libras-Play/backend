from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.core.config import get_settings

settings = get_settings()

# Convertir DATABASE_URL a formato asyncpg si es necesario
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Engine async para PostgreSQL
engine = create_async_engine(
    database_url,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=False,  # Disabled for testing to avoid event loop issues
)

# Session maker async
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base para modelos SQLAlchemy
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency para obtener sesión de base de datos.
    Uso en FastAPI: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Inicializa la base de datos creando todas las tablas"""
    try:
        # Import all models to register them with Base.metadata
        from app import models  # noqa: F401
        
        async with engine.begin() as conn:
            # Check if tables already exist
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'languages'
                );
            """))
            tables_exist = result.scalar()
            
            if not tables_exist:
                # Only create tables if they don't exist
                await conn.run_sync(Base.metadata.create_all)
                print("✓ Database tables created successfully")
            else:
                print("✓ Database tables already exist, skipping creation")
                
    except Exception as e:
        # Log full error details but don't crash
        import traceback
        error_details = traceback.format_exc()
        print(f"Warning: Could not initialize database: {e}")
        print(f"Full error: {error_details}")
        # Don't fail if database is not available (for cloud deployment without RDS)


async def close_db():
    """Cierra el engine de la base de datos"""
    try:
        await engine.dispose()
    except Exception as e:
        print(f"Warning: Could not dispose database engine: {e}")
