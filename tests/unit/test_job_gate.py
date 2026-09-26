import threading

from sniplingo.core.job_gate import LatestJobGate


def test_newly_issued_job_is_current():
    gate = LatestJobGate()
    job = gate.issue()
    assert gate.is_current(job)


def test_issuing_a_new_job_makes_older_ones_stale():
    gate = LatestJobGate()
    first = gate.issue()
    second = gate.issue()
    assert not gate.is_current(first)
    assert gate.is_current(second)


def test_ids_are_unique_and_increasing():
    gate = LatestJobGate()
    ids = [gate.issue() for _ in range(5)]
    assert ids == sorted(set(ids))


def test_unknown_id_is_not_current():
    assert not LatestJobGate().is_current(0)


def test_concurrent_issue_never_hands_out_duplicate_ids():
    gate = LatestJobGate()
    ids: list[int] = []
    lock = threading.Lock()

    def worker():
        for _ in range(500):
            job = gate.issue()
            with lock:
                ids.append(job)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(ids) == len(set(ids)) == 2000
    assert gate.is_current(max(ids))
