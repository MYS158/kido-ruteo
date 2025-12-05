"""CLI entrypoint to run only the matrix generation stage."""
from kido_ruteo.pipeline import generate_matrices


if __name__ == "__main__":
    generate_matrices()
