"""Testes unitários dos modelos de domínio e invariantes de validação."""

from dataclasses import FrozenInstanceError

import pytest

from src.domain import (
    InvalidSchedulingInputError,
    ProcessedSurgery,
    SchedulingResult,
    ShiftConfig,
    ShiftWindow,
    SurgeryRequest,
    SurgeryType,
)


class TestDomainModelsHappyPath:
    """Casos de caminho feliz (TP-01) para construção e imutabilidade do domínio."""

    def test_valid_surgery_request_defaults_and_immutability(self) -> None:
        """TP-01: Verifica padrões clássicos e bloqueio de mutação em SurgeryRequest."""
        surgery = SurgeryRequest(surgery_id="S1", start_time=480, finish_time=540)

        assert surgery.surgery_id == "S1"
        assert surgery.start_time == 480
        assert surgery.finish_time == 540
        assert surgery.surgery_type == SurgeryType.CLEAN
        assert surgery.sterilization_duration == 0

        with pytest.raises(FrozenInstanceError):
            surgery.finish_time = 600  # type: ignore[misc]

    def test_valid_contaminated_surgery_and_shift_config(self) -> None:
        """TP-01: Verifica criação válida de cirurgia contaminada e janela de turno."""
        contaminated = SurgeryRequest(
            surgery_id="S2",
            start_time=600,
            finish_time=660,
            surgery_type=SurgeryType.CONTAMINATED,
            sterilization_duration=45,
        )
        window = ShiftWindow(start=720, end=780)
        config = ShiftConfig(closing_horizon=1080, shift_window=window)
        processed = ProcessedSurgery(request=contaminated, effective_release_time=705)
        result = SchedulingResult(
            algorithm_name="Classic Test",
            selected_surgeries=(processed,),
            total_selected=1,
            discarded_infeasible_count=0,
            elapsed_ns=1500,
        )

        assert config.closing_horizon == 1080
        assert config.shift_window == window
        assert processed.effective_release_time == 705
        assert result.total_selected == 1


class TestDomainModelsValidationErrors:
    """Casos de falha e borda (TE-01) garantindo rejeição de entradas inválidas."""

    @pytest.mark.parametrize(
        ("kwargs"),
        [
            {"surgery_id": "", "start_time": 10, "finish_time": 20},
            {"surgery_id": "   ", "start_time": 10, "finish_time": 20},
            {"surgery_id": "S1", "start_time": -1, "finish_time": 20},
            {"surgery_id": "S1", "start_time": 20, "finish_time": 20},
            {"surgery_id": "S1", "start_time": 30, "finish_time": 20},
            {"surgery_id": "S1", "start_time": True, "finish_time": 20},
            {
                "surgery_id": "S1",
                "start_time": 10,
                "finish_time": 20,
                "surgery_type": SurgeryType.CLEAN,
                "sterilization_duration": 15,
            },
            {
                "surgery_id": "S1",
                "start_time": 10,
                "finish_time": 20,
                "surgery_type": SurgeryType.CONTAMINATED,
                "sterilization_duration": 0,
            },
            {
                "surgery_id": "S1",
                "start_time": 10,
                "finish_time": 20,
                "surgery_type": SurgeryType.CONTAMINATED,
                "sterilization_duration": -5,
            },
        ],
    )
    def test_invalid_surgery_request_raises_domain_error(
        self, kwargs: dict[str, object]
    ) -> None:
        """TE-01: Entradas malformadas em SurgeryRequest devem lançar InvalidSchedulingInputError."""
        with pytest.raises(InvalidSchedulingInputError):
            SurgeryRequest(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("start", "end"),
        [
            (-10, 20),
            (50, 50),
            (60, 40),
            (False, 10),
        ],
    )
    def test_invalid_shift_window_raises_domain_error(
        self, start: object, end: object
    ) -> None:
        """TE-01: ShiftWindow inválida deve lançar InvalidSchedulingInputError."""
        with pytest.raises(InvalidSchedulingInputError):
            ShiftWindow(start=start, end=end)  # type: ignore[arg-type]

    def test_invalid_shift_config_raises_domain_error(self) -> None:
        """TE-01: Horizonte não positivo ou janela fora do horizonte deve falhar."""
        with pytest.raises(InvalidSchedulingInputError):
            ShiftConfig(closing_horizon=0)

        with pytest.raises(InvalidSchedulingInputError):
            ShiftConfig(
                closing_horizon=750,
                shift_window=ShiftWindow(start=720, end=780),
            )

    def test_invalid_processed_surgery_and_result_raise_domain_error(self) -> None:
        """TE-01: Inconsistências em ProcessedSurgery e SchedulingResult devem falhar."""
        surgery = SurgeryRequest(surgery_id="S1", start_time=10, finish_time=20)
        with pytest.raises(InvalidSchedulingInputError):
            ProcessedSurgery(request=surgery, effective_release_time=19)

        processed = ProcessedSurgery(request=surgery, effective_release_time=20)
        with pytest.raises(InvalidSchedulingInputError):
            SchedulingResult(
                algorithm_name="Classic",
                selected_surgeries=(processed,),
                total_selected=2,
                discarded_infeasible_count=0,
                elapsed_ns=10,
            )
