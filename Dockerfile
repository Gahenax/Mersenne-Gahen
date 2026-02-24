# Dockerfile OEDA-JULES L2 (Hodge-Rigidity)
# Inyectado por Antigravity
# Propósito: Contenerizar la simulación de Estructuras de Hodge (Chronos) para su despacho al clúster Jules,
# garantizando cero impacto en el CPU o la memoria del PC host.

FROM continuumio/miniconda3:latest

# Meta-datos
LABEL maintainer="Gahenax"
LABEL component="Jules L2 - Science Node"
LABEL experiment="Hodge Rigidity & VHS"

# Establecer directorio de trabajo L2
WORKDIR /app/jules_workspace

# Copiar el manifiesto de la orden
COPY environment.yml .
COPY requirements.txt .

# Configurar el ambiente hermético
RUN conda env update --file environment.yml --name base || echo "No conda env to update"
RUN pip install --no-cache-dir -r requirements.txt || echo "No pip reqs"
RUN pip install --no-cache-dir pytest flake8 numpy scipy sympy networkx mpmath ruff

# Copiar todo el laboratorio simulado
COPY . /app/jules_workspace/

# Punto de entrada predeterminado al invocar este contenedor en Jules
CMD ["python", "lab/simulations/chronos_hodge_experiment.py"]
