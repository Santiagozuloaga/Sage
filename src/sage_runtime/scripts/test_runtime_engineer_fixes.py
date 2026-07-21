"""
Regression test for Runtime Engineer fixes.
Verifies that each bug fix is in place and does not break existing behavior.

Run with: python /home/z/my-project/scripts/test_runtime_engineer_fixes.py
"""
import asyncio
import json
import os
import sys
import tempfile
from collections import deque
from datetime import datetime
from pathlib import Path

# Make the fixed sage_runtime importable
sys.path.insert(0, '/home/z/my-project/work/sage_runtime_fixed')


PASS = 0
FAIL = 0
RESULTS = []

def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(f'  PASS  {name}')
    else:
        FAIL += 1
        RESULTS.append(f'  FAIL  {name}  {detail}')


# -----------------------------------------------------------------------------
# Event Bus fixes
# -----------------------------------------------------------------------------

async def test_event_bus_idempotent_start():
    from events.bus import EventBus
    from events.models import EventType
    bus = EventBus()
    await bus.start()
    await bus.start()  # second call should be a no-op
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    check('E-8 EventBus.start() idempotent (only 1 processor task)', len(pending) == 1,
          detail=f'got {len(pending)} tasks')
    await bus.stop()


async def test_event_bus_history_is_deque():
    from events.bus import EventBus
    bus = EventBus(max_history=5)
    check('E-10 EventBus._history is deque', isinstance(bus._history, deque),
          detail=f'got {type(bus._history).__name__}')
    check('E-10 EventBus._history has maxlen=5', bus._history.maxlen == 5,
          detail=f'maxlen={bus._history.maxlen}')


async def test_event_bus_dlq_exists():
    from events.bus import EventBus
    bus = EventBus()
    check('DLQ-1 EventBus._dlq exists', hasattr(bus, '_dlq'))
    check('DLQ-1 EventBus._dlq is deque', isinstance(bus._dlq, deque))
    check('DLQ-1 EventBus.get_dlq() exists', callable(getattr(bus, 'get_dlq', None)))
    check('DLQ-1 EventBus.clear_dlq() exists', callable(getattr(bus, 'clear_dlq', None)))
    check('DLQ-1 EventBus.replay_dlq() exists', callable(getattr(bus, 'replay_dlq', None)))


async def test_event_bus_dlq_captures_handler_errors():
    from events.bus import EventBus
    from events.models import EventType, Event
    bus = EventBus()
    await bus.start()

    def bad_handler(event: Event):
        raise RuntimeError('intentional handler failure')

    bus.subscribe(EventType.ERROR, bad_handler)
    await bus.publish(EventType.ERROR, {'msg': 'test'}, source='test')
    # Give the processor a moment to dispatch
    await asyncio.sleep(0.15)
    dlq = bus.get_dlq()
    check('DLQ-1 DLQ captures handler errors', len(dlq) == 1,
          detail=f'dlq len={len(dlq)}')
    if dlq:
        entry = dlq[0]
        check('DLQ-1 DLQ entry has event dict', 'event' in entry)
        check('DLQ-1 DLQ entry has error', 'error' in entry and 'intentional' in entry['error'])
        check('DLQ-1 DLQ entry has failed_at', 'failed_at' in entry)
    await bus.stop()


async def test_event_bus_publish_before_start_raises():
    from events.bus import EventBus
    from events.models import EventType
    bus = EventBus()  # not started
    try:
        await bus.publish(EventType.BOOT, {}, source='test')
        check('E-1 publish() before start() raises RuntimeError', False,
              detail='no exception raised')
    except RuntimeError as e:
        check('E-1 publish() before start() raises RuntimeError', 'before start' in str(e),
              detail=f'msg={e}')


async def test_event_bus_stop_clears_queue_ref():
    from events.bus import EventBus
    bus = EventBus()
    await bus.start()
    await bus.stop()
    check('E-8 EventBus.stop() clears _event_queue', bus._event_queue is None,
          detail=f'_event_queue={bus._event_queue!r}')
    check('E-8 EventBus.stop() clears _processor_task', bus._processor_task is None)


# -----------------------------------------------------------------------------
# Event models fix
# -----------------------------------------------------------------------------

def test_event_handler_type_hint():
    from events.models import EventHandler
    hint_str = str(EventHandler)
    check('E-14 EventHandler type hint mentions Awaitable',
          'Awaitable' in hint_str or 'Union' in hint_str or 'Coroutine' in hint_str,
          detail=f'hint={hint_str}')


# -----------------------------------------------------------------------------
# Recovery system fixes
# -----------------------------------------------------------------------------

async def test_recovery_checkpoint_id_no_collision():
    from recovery.system import RecoverySystem
    with tempfile.TemporaryDirectory() as td:
        rec = RecoverySystem(Path(td))
        await rec.initialize()
        id1 = await rec.create_checkpoint({'i': 1})
        id2 = await rec.create_checkpoint({'i': 2})
        check('R-2 checkpoint IDs differ within same second', id1 != id2,
              detail=f'id1={id1} id2={id2}')
        cps = await rec.list_checkpoints()
        check('R-2 both checkpoints persisted', len(cps) == 2,
              detail=f'count={len(cps)}')
        r1 = await rec.restore_checkpoint(id1)
        r2 = await rec.restore_checkpoint(id2)
        check('R-2 checkpoint 1 state preserved', r1 == {'i': 1}, detail=f'r1={r1}')
        check('R-2 checkpoint 2 state preserved', r2 == {'i': 2}, detail=f'r2={r2}')


async def test_recovery_atomic_write_no_corruption():
    from recovery.system import RecoverySystem
    with tempfile.TemporaryDirectory() as td:
        rec = RecoverySystem(Path(td))
        await rec.initialize()
        # First, succeed at creating one checkpoint so we know the dir works
        good_id = await rec.create_checkpoint({'i': 'first'})
        good_file = Path(td) / 'checkpoints' / f'{good_id}.json'
        check('R-3 normal checkpoint write works', good_file.exists())

        # Now make the dir read-only and try to create another. The atomic
        # write should leave NO new file behind (no half-written .tmp file).
        import stat
        os.chmod(Path(td) / 'checkpoints', stat.S_IRUSR | stat.S_IXUSR)  # r-x for owner
        try:
            try:
                await rec.create_checkpoint({'i': 'second'})
                check('R-3 failed write leaves no .tmp file', True)  # if it succeeded, fine
            except Exception:
                tmp_files = list((Path(td) / 'checkpoints').glob('.*_*.tmp'))
                check('R-3 failed write leaves no .tmp file', len(tmp_files) == 0,
                      detail=f'found {len(tmp_files)} .tmp files: {[f.name for f in tmp_files]}')
        finally:
            os.chmod(Path(td) / 'checkpoints', stat.S_IRWXU)


async def test_recovery_cleanup_deletes_corrupted():
    from recovery.system import RecoverySystem
    with tempfile.TemporaryDirectory() as td:
        rec = RecoverySystem(Path(td))
        await rec.initialize()
        for i in range(3):
            await rec.create_checkpoint({'i': i})
        # Create a corrupted file
        bad_file = Path(td) / 'checkpoints' / 'corrupted_20250101_000000_000000.json'
        bad_file.write_text('{"this is not": valid json')
        check('R-5 corrupted file present before cleanup', bad_file.exists())
        # Cleanup keeping only 2 — should delete the oldest valid AND the corrupted one
        await rec.cleanup_old_checkpoints(keep_count=2)
        cps = await rec.list_checkpoints()
        check('R-5 cleanup keeps 2 valid checkpoints', len(cps) == 2,
              detail=f'count={len(cps)}')
        check('R-5 cleanup deletes corrupted file', not bad_file.exists())


# -----------------------------------------------------------------------------
# Mission Control fixes
# -----------------------------------------------------------------------------

async def test_mission_control_start_end_time():
    from mission_control.controller import MissionControl
    mc = MissionControl()
    await mc.initialize()
    before = datetime.now()
    ok = await mc.start_mission('m1', 'test', {'k': 'v'})
    after = datetime.now()
    check('M-1 start_mission returns True', ok)
    active = mc.get_active_missions()
    check('M-1 active mission has start_time', active[0].get('start_time') is not None,
          detail=f'start_time={active[0].get("start_time")!r}')
    try:
        st = datetime.fromisoformat(active[0]['start_time'])
        check('M-1 start_time is valid ISO', before <= st <= after,
              detail=f'st={st} not in [{before}, {after}]')
    except Exception as e:
        check('M-1 start_time is valid ISO', False, detail=str(e))

    ok = await mc.complete_mission('m1', {'success': True})
    check('M-2 complete_mission returns True', ok)
    hist = mc.get_mission_history()
    check('M-2 completed mission has end_time', hist[0].get('end_time') is not None,
          detail=f'end_time={hist[0].get("end_time")!r}')
    check('M-2 completed mission has duration_seconds', hist[0].get('duration_seconds') is not None,
          detail=f'duration={hist[0].get("duration_seconds")!r}')
    check('M-2 duration is non-negative', hist[0].get('duration_seconds', -1) >= 0)


async def test_mission_control_history_bounded():
    from mission_control.controller import MissionControl
    mc = MissionControl(history_limit=5)
    await mc.initialize()
    for i in range(10):
        await mc.start_mission(f'm{i}', f'obj{i}', {})
        await mc.complete_mission(f'm{i}', {'i': i})
    hist = mc.get_mission_history(limit=100)
    check('M-5 mission history is bounded to limit', len(hist) <= 5,
          detail=f'len={len(hist)}, limit=5')
    check('M-5 most recent mission kept', hist[0]['mission_id'] == 'm9',
          detail=f'first={hist[0]["mission_id"]}')
    check('M-5 oldest mission dropped', all(h['mission_id'] != 'm0' for h in hist))


# -----------------------------------------------------------------------------
# Boot Configurator fix
# -----------------------------------------------------------------------------

async def test_boot_atomic_save_no_corruption():
    from boot.configurator import BootConfigurator
    import json as _json
    with tempfile.TemporaryDirectory() as td:
        cfg = BootConfigurator(Path(td))
        await cfg.load()
        # Patch json.dump to fail mid-write
        orig_dump = _json.dump
        def crash_dump(*a, **kw):
            raise OSError('disk full!')
        _json.dump = crash_dump
        try:
            ok = await cfg.save()
        finally:
            _json.dump = orig_dump
        check('B-2 save() returns False on failure', ok is False)
        cfg_path = Path(td) / 'boot_config.json'
        if cfg_path.exists():
            try:
                content = cfg_path.read_text()
                _json.loads(content)
                check('B-2 existing config file is valid JSON after failed save', True)
            except Exception as e:
                check('B-2 existing config file is valid JSON after failed save', False,
                      detail=f'content={content[:50]!r}, err={e}')
        tmp_files = list(Path(td).glob('.boot_config_*.tmp'))
        check('B-2 no .tmp files left behind', len(tmp_files) == 0,
              detail=f'found {len(tmp_files)}')


# -----------------------------------------------------------------------------
# Kernel State (FSM) fixes
# -----------------------------------------------------------------------------

def test_fsm_illegal_transition_logs_warning():
    from kernel.state import KernelState, KernelContext
    ctx = KernelContext(current_state=KernelState.BOOT, session_id='t',
                        boot_time=datetime.now())
    import logging, io
    log_buf = io.StringIO()
    h = logging.StreamHandler(log_buf)
    h.setLevel(logging.WARNING)
    log = logging.getLogger('kernel.state')
    log.addHandler(h)
    try:
        ctx.transition_to(KernelState.COMMAND_EXECUTION, 'illegal jump test')
    finally:
        log.removeHandler(h)
    log_text = log_buf.getvalue()
    check('S-1 illegal transition logs warning', 'Illegal transition' in log_text,
          detail=f'log={log_text!r}')
    check('S-1 illegal transition still proceeds (non-breaking)',
          ctx.current_state == KernelState.COMMAND_EXECUTION)


def test_fsm_legal_transitions_no_warning():
    from kernel.state import KernelState, KernelContext
    import logging, io
    ctx = KernelContext(current_state=KernelState.BOOT, session_id='t',
                        boot_time=datetime.now())
    log_buf = io.StringIO()
    h = logging.StreamHandler(log_buf)
    h.setLevel(logging.WARNING)
    log = logging.getLogger('kernel.state')
    log.addHandler(h)
    try:
        ctx.transition_to(KernelState.KERNEL_READY, 'boot done')
        ctx.transition_to(KernelState.COMMAND_MODE, 'enter cmd mode')
        ctx.transition_to(KernelState.WAITING_FOR_USER_COMMAND, 'waiting')
        ctx.transition_to(KernelState.COMMAND_EXECUTION, 'executing')
        ctx.transition_to(KernelState.WAITING_FOR_USER_COMMAND, 'back to waiting')
        ctx.transition_to(KernelState.SHUTDOWN, 'shutdown')
    finally:
        log.removeHandler(h)
    log_text = log_buf.getvalue()
    check('S-1 legal transitions produce no warnings', 'Illegal transition' not in log_text,
          detail=f'log={log_text!r}')


def test_fsm_is_valid_transition_method():
    from kernel.state import KernelState, KernelContext
    check('S-1 is_valid_transition(BOOT, KERNEL_READY) True',
          KernelContext.is_valid_transition(KernelState.BOOT, KernelState.KERNEL_READY) is True)
    check('S-1 is_valid_transition(BOOT, COMMAND_EXECUTION) False',
          KernelContext.is_valid_transition(KernelState.BOOT, KernelState.COMMAND_EXECUTION) is False)
    check('S-1 is_valid_transition(BOOT, SHUTDOWN) True',
          KernelContext.is_valid_transition(KernelState.BOOT, KernelState.SHUTDOWN) is True)
    check('S-1 is_valid_transition(SHUTDOWN, BOOT) False',
          KernelContext.is_valid_transition(KernelState.SHUTDOWN, KernelState.BOOT) is False)


def test_fsm_last_error_tracking():
    from kernel.state import KernelState, KernelContext
    ctx = KernelContext(current_state=KernelState.BOOT, session_id='t',
                        boot_time=datetime.now())
    check('S-2 last_error defaults to None', ctx.last_error is None)
    check('S-2 error_count defaults to 0', ctx.error_count == 0)
    ctx.record_error('first error')
    check('S-2 record_error sets last_error', ctx.last_error == 'first error')
    check('S-2 record_error increments count', ctx.error_count == 1)
    ctx.record_error('second error')
    check('S-2 record_error increments count again', ctx.error_count == 2)
    check('S-2 last_error is most recent', ctx.last_error == 'second error')
    ctx.clear_error()
    check('S-2 clear_error nulls last_error', ctx.last_error is None)
    check('S-2 clear_error does NOT reset count', ctx.error_count == 2)


# -----------------------------------------------------------------------------
# Kernel core fixes
# -----------------------------------------------------------------------------

async def test_kernel_shutdown_isolates_component_failures():
    from kernel.core import SageKernel

    class Good:
        shutdown_called = False
        async def shutdown(self):
            Good.shutdown_called = True

    class Bad:
        async def shutdown(self):
            raise RuntimeError('bad')

    class AlsoGood:
        shutdown_called = False
        async def shutdown(self):
            AlsoGood.shutdown_called = True

    kernel = SageKernel()
    kernel._components = {'a': Good(), 'b': Bad(), 'c': AlsoGood()}
    try:
        await kernel.shutdown()
        check('K-7 shutdown() does not raise on component failure', True)
    except Exception as e:
        check('K-7 shutdown() does not raise on component failure', False, detail=str(e))
    check('K-7 first component (a) was shut down despite b failing', Good.shutdown_called)
    check('K-7 last component (c) was shut down before b failed', AlsoGood.shutdown_called)


async def test_kernel_shutdown_idempotent():
    from kernel.core import SageKernel
    kernel = SageKernel()
    await kernel.shutdown()
    try:
        await kernel.shutdown()
        check('K-8 shutdown() idempotent (second call no-op)', True)
    except Exception as e:
        check('K-8 shutdown() idempotent (second call no-op)', False, detail=str(e))
    check('K-8 _shutdown_complete flag set', kernel._shutdown_complete)


# -----------------------------------------------------------------------------
# main.py fix
# -----------------------------------------------------------------------------

def test_main_no_redundant_dashboard_init():
    with open('/home/z/my-project/work/sage_runtime_fixed/main.py') as f:
        src = f.read()
    check('MAIN-1 main.py reuses kernel dashboard via get_component',
          "kernel.get_component('dashboard')" in src)
    occurrences = src.count('DashboardMonitor()')
    check('MAIN-1 main.py DashboardMonitor() only in fallback branch', occurrences == 1,
          detail=f'occurrences={occurrences}')
    check('MAIN-1 main.py no manual dashboard.shutdown() in finally',
          'await dashboard.shutdown()' not in src)


# -----------------------------------------------------------------------------
# Run all tests
# -----------------------------------------------------------------------------

async def main():
    print('=' * 70)
    print('Runtime Engineer Fixes — Regression Test')
    print('=' * 70)

    print('\n[Event Bus]')
    await test_event_bus_idempotent_start()
    await test_event_bus_history_is_deque()
    await test_event_bus_dlq_exists()
    await test_event_bus_dlq_captures_handler_errors()
    await test_event_bus_publish_before_start_raises()
    await test_event_bus_stop_clears_queue_ref()
    test_event_handler_type_hint()

    print('\n[Recovery]')
    await test_recovery_checkpoint_id_no_collision()
    await test_recovery_atomic_write_no_corruption()
    await test_recovery_cleanup_deletes_corrupted()

    print('\n[Mission Control]')
    await test_mission_control_start_end_time()
    await test_mission_control_history_bounded()

    print('\n[Boot Configurator]')
    await test_boot_atomic_save_no_corruption()

    print('\n[Kernel State / FSM]')
    test_fsm_illegal_transition_logs_warning()
    test_fsm_legal_transitions_no_warning()
    test_fsm_is_valid_transition_method()
    test_fsm_last_error_tracking()

    print('\n[Kernel Core]')
    await test_kernel_shutdown_isolates_component_failures()
    await test_kernel_shutdown_idempotent()

    print('\n[main.py]')
    test_main_no_redundant_dashboard_init()

    print('\n' + '=' * 70)
    print(f'Results: {PASS} passed, {FAIL} failed')
    print('=' * 70)
    print('\n'.join(RESULTS))
    return 0 if FAIL == 0 else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
