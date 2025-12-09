"""CLI entrypoint to run the full KIDO pipeline."""
import logging

from kido_ruteo.config.loader import ConfigLoader
from kido_ruteo.pipeline import run_kido_pipeline


def main() -> None:
    """Execute the full KIDO pipeline with default configuration."""
    # Setup logging to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(console_handler)
    
    logging.info("Loading configuration...")
    cfg = ConfigLoader.load_all()
    
    logging.info("Starting KIDO pipeline...")
    result = run_kido_pipeline(cfg, fix_disconnected_nodes=True)
    
    logging.info("Pipeline completed successfully!")
    logging.info("Results: processed=%d, routing=%d, validation=%d", 
                 len(result["processed"]), len(result["routing"]), len(result["validation"]))


if __name__ == "__main__":
    main()
