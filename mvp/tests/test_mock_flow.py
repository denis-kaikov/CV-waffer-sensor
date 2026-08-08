from app.application.controller import ControlCommand, InspectionController
from app.camera.base import CameraConfig
from app.camera.manager import CameraManager
from app.modbus.server import ModbusBridge
from app.processing.base import OverallResult, SlotState
from app.processing.hybrid import HybridProcessor


def test_mock_flow_returns_safe_error():
    manager = CameraManager()
    manager.add("mock", CameraConfig(camera_id="cassette_left"))
    controller = InspectionController(manager, HybridProcessor())
    controller.initialize()
    result = controller.inspect(ControlCommand(1, "cassette_left", 200))
    assert result.overall == OverallResult.ERROR


def test_slot_state_codes_match_dataset_and_modbus_contract():
    assert {
        state.name: int(state)
        for state in SlotState
    } == {
        "EMPTY": 0,
        "OCCUPIED_OK": 1,
        "CROSS_SLOT": 2,
        "SHIFTED_IN_SLOT": 3,
        "DOUBLE_LOADED_SUSPECT": 4,
        "UNCERTAIN": 5,
    }


def test_modbus_bridge_uses_supported_pymodbus_api():
    controller = InspectionController(CameraManager(), HybridProcessor())
    bridge = ModbusBridge(controller, ["cassette_left"])

    assert bridge.camera_ids == ["cassette_left"]
