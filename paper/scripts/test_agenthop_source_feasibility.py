"""Small overlap checks for the external AgentHop source audit."""

from agenthop_source_feasibility import Components


def test_components_merge_transitive_shared_papers():
    components = Components(4)
    components.add(0, {"seed-a", "bridge-x"})
    components.add(1, {"seed-b", "bridge-x", "gold-y"})
    components.add(2, {"seed-c", "gold-y"})
    components.add(3, {"seed-d"})
    assert components.sizes() == [3, 1]


def test_components_keep_disjoint_seeds_separate():
    components = Components(3)
    for index in range(3):
        components.add(index, {f"seed-{index}", f"target-{index}"})
    assert components.sizes() == [1, 1, 1]
