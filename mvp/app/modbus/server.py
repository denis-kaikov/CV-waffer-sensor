from __future__ import annotations

import asyncio
import logging

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartAsyncTcpServer

from app.application.controller import ControlCommand, InspectionController
from app.processing.base import OverallResult
from . import register_map as rm

log = logging.getLogger(__name__)


class ModbusBridge:
    def __init__(self, controller: InspectionController, camera_ids: list[str]) -> None:
        self.controller = controller
        self.camera_ids = camera_ids
        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0] * 1000),
            co=ModbusSequentialDataBlock(0, [0] * 1000),
            hr=ModbusSequentialDataBlock(0, [0] * 1000),
            ir=ModbusSequentialDataBlock(0, [0] * 1000),
            zero_mode=True,
        )
        self.context = ModbusServerContext(slaves=store, single=True)
        self._last_seen_command_id = -1
        self._heartbeat = 0

    def _slave(self):
        return self.context[0]

    async def poll(self) -> None:
        while True:
            slave = self._slave()
            command_id = slave.getValues(3, rm.HR_COMMAND_ID, count=1)[0]
            camera_index = slave.getValues(3, rm.HR_CAMERA_ID, count=1)[0]
            cassette_type = slave.getValues(3, rm.HR_CASSETTE_TYPE, count=1)[0]
            command = slave.getValues(3, rm.HR_COMMAND, count=1)[0]

            if command == rm.COMMAND_INSPECT and command_id != self._last_seen_command_id:
                self._last_seen_command_id = command_id
                camera_id = self.camera_ids[max(0, min(camera_index, len(self.camera_ids) - 1))]
                result = await asyncio.to_thread(
                    self.controller.inspect,
                    ControlCommand(command_id=command_id, camera_id=camera_id, cassette_type_mm=cassette_type),
                )
                self._publish_result(command_id, result)
                slave.setValues(3, rm.HR_COMMAND, [rm.COMMAND_NONE])
            elif command == rm.COMMAND_ACK:
                self.controller.acknowledge()
                slave.setValues(3, rm.HR_COMMAND, [rm.COMMAND_NONE])
            elif command == rm.COMMAND_RESET_ERROR:
                self.controller.reset_error()
                slave.setValues(3, rm.HR_COMMAND, [rm.COMMAND_NONE])

            self._heartbeat = (self._heartbeat + 1) & 0xFFFF
            slave.setValues(4, rm.IR_STATE, [int(self.controller.state)])
            slave.setValues(4, rm.IR_APP_HEARTBEAT, [self._heartbeat])
            await asyncio.sleep(0.05)

    def _publish_result(self, command_id: int, result) -> None:
        slave = self._slave()
        duration = self.controller.processing_time_ms
        values = [
            command_id & 0xFFFF,
            int(self.controller.state),
            int(result.overall),
            result.error_code & 0xFFFF,
            (duration >> 16) & 0xFFFF,
            duration & 0xFFFF,
            len(result.slots) & 0xFFFF,
        ]
        slave.setValues(4, rm.IR_RESULT_COMMAND_ID, values)
        if result.slots:
            slave.setValues(4, rm.IR_SLOT_MAP_START, [int(slot) for slot in result.slots])


async def run_modbus_server(controller: InspectionController, camera_ids: list[str], host: str, port: int) -> None:
    bridge = ModbusBridge(controller, camera_ids)
    poll_task = asyncio.create_task(bridge.poll())
    try:
        await StartAsyncTcpServer(context=bridge.context, address=(host, port))
    finally:
        poll_task.cancel()
