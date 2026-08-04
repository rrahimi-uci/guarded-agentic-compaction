from __future__ import annotations

import matplotlib.pyplot as plt

import build_artifacts


def test_generated_figure_bytes_are_stable(monkeypatch, tmp_path):
    monkeypatch.setattr(build_artifacts, "FIGURES", tmp_path)
    build_artifacts.configure_plots()

    def render() -> tuple[bytes, bytes]:
        _, axis = plt.subplots(figsize=(2.0, 1.0))
        axis.plot([0, 1], [1, 0])
        build_artifacts.savefig("stable")
        return (
            (tmp_path / "stable.pdf").read_bytes(),
            (tmp_path / "stable.png").read_bytes(),
        )

    assert render() == render()
