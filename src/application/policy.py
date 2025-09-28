from dataclasses import dataclass
@dataclass
class Policy:
    BLOCK_THRESHOLD: float = 0.88   # <- substitua pelos 'best' do relatório
    SANITIZE_THRESHOLD: float = 0.62

