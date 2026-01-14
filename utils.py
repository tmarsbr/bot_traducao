# Utilitários para o agente de tradução de vídeos

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from logger_config import setup_logger

logger = setup_logger(__name__)

class VideoTranslationMetrics:
    """Classe para rastrear métricas de tradução."""
    
    def __init__(self, video_name: str, target_language: str):
        self.video_name = video_name
        self.target_language = target_language
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.api_requests = 0
        self.tokens_used = 0
        self.errors: list[str] = []
        self.stages_completed: Dict[str, bool] = {
            "extract": False,
            "transcribe": False,
            "translate": False,
            "embed": False,
        }
    
    def add_error(self, stage: str, error_msg: str):
        """Registra um erro ocorrido durante o processamento."""
        self.errors.append(f"[{stage}] {error_msg}")
        logger.error(f"Erro em {stage}: {error_msg}")
    
    def complete_stage(self, stage: str):
        """Marca um estágio como concluído."""
        if stage in self.stages_completed:
            self.stages_completed[stage] = True
            logger.info(f"Estágio '{stage}' concluído com sucesso")
    
    def finish(self):
        """Marca o fim do processamento."""
        self.end_time = datetime.now()
    
    def get_duration(self) -> float:
        """Retorna a duração em segundos."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte métricas para dicionário."""
        return {
            "video_name": self.video_name,
            "target_language": self.target_language,
            "duration_seconds": self.get_duration(),
            "api_requests": self.api_requests,
            "tokens_used": self.tokens_used,
            "stages_completed": self.stages_completed,
            "errors": self.errors,
            "status": "success" if not self.errors else "completed_with_errors",
        }
    
    def save_report(self, output_dir: Path):
        """Salva relatório em JSON."""
        report_file = output_dir / f"report_{self.video_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Relatório salvo em: {report_file}")


def validate_input_file(file_path: str, supported_formats: list[str]) -> bool:
    """
    Valida se o arquivo de entrada existe e tem extensão suportada.
    
    Args:
        file_path: Caminho do arquivo
        supported_formats: Lista de extensões suportadas
        
    Returns:
        bool: True se válido, False caso contrário
    """
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"Arquivo não encontrado: {file_path}")
        return False
    
    if path.suffix.lower() not in supported_formats:
        logger.error(f"Formato não suportado: {path.suffix}. Suportados: {supported_formats}")
        return False
    
    return True


def get_file_size_mb(file_path: str) -> float:
    """Retorna o tamanho do arquivo em MB."""
    return os.path.getsize(file_path) / (1024 * 1024)


def format_timestamp(seconds: float) -> str:
    """Converte segundos para formato SRT (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
