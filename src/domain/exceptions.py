"""Exceções específicas do domínio de escalonamento cirúrgico."""


class InvalidSchedulingInputError(ValueError):
    """Exceção lançada quando os parâmetros de entrada violam invariantes do domínio."""
