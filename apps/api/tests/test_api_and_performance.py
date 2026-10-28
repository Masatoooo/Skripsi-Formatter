from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app, reset_rate_limiter
from tests.fixture_builder import ensure_all_fixtures

client = TestClient(app)


def test_full_api_contract_lifecycle():
    reset_rate_limiter()
    fixtures_dir = ensure_all_fixtures()
    src_bytes = (fixtures_dir / "manual_formatting.docx").read_bytes()

    # 1. GET /v1/profiles
    prof_res = client.get("/v1/profiles")
    assert prof_res.status_code == 200
    profiles = prof_res.json()
    assert any(p["profile_id"] == "contoh-s1-skripsi" for p in profiles)
    assert any(p["profile_id"] == "contoh-s1-teknik" for p in profiles)

    # 2. POST /v1/documents
    up_res = client.post(
        "/v1/documents",
        files={"file": ("manual_formatting.docx", src_bytes, "application/octet-stream")},
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["doc_id"]

    # 3. POST /v1/documents/{id}/analyze
    an_res = client.post(
        f"/v1/documents/{doc_id}/analyze",
        json={"profile_id": "contoh-s1-skripsi"},
    )
    assert an_res.status_code == 200
    an_data = an_res.json()
    assert an_data["total_findings"] > 0
    job_id = an_data["job_id"]

    # 4. GET /v1/jobs/{job_id}
    job_res = client.get(f"/v1/jobs/{job_id}")
    assert job_res.status_code == 200
    assert job_res.json()["status"] == "done"

    # 5. GET /v1/documents/{id}/findings (with filters)
    f_res = client.get(f"/v1/documents/{doc_id}/findings?category=FONT")
    assert f_res.status_code == 200
    assert all(f["category"] == "FONT" for f in f_res.json()["findings"])

    # 6. GET & PUT /v1/documents/{id}/roles
    r_res = client.get(f"/v1/documents/{doc_id}/roles")
    assert r_res.status_code == 200
    assert len(r_res.json()["roles"]) > 0

    put_r_res = client.put(
        f"/v1/documents/{doc_id}/roles",
        json={"roles": [{"block_index": 0, "role": "chapter_label"}]},
    )
    assert put_r_res.status_code == 200
    assert put_r_res.json()["roles"][0]["user_confirmed"] is True

    # 7. POST /v1/documents/{id}/fix
    fix_res = client.post(
        f"/v1/documents/{doc_id}/fix",
        json={
            "profile_id": "contoh-s1-skripsi",
            "mode": "all",
            "approved_suggest_ids": ["PARA-005", "PARA-006", "HEAD-003"],
        },
    )
    assert fix_res.status_code == 200
    assert fix_res.json()["total_changes"] > 0

    # 8. GET /v1/documents/{id}/changelog
    cl_res = client.get(f"/v1/documents/{doc_id}/changelog")
    assert cl_res.status_code == 200
    assert cl_res.json()["total_changes"] == fix_res.json()["total_changes"]

    # 9. GET /v1/documents/{id}/report?format=json and format=html
    rep_json = client.get(f"/v1/documents/{doc_id}/report?format=json")
    assert rep_json.status_code == 200
    assert rep_json.json()["doc_id"] == doc_id

    rep_html = client.get(f"/v1/documents/{doc_id}/report?format=html")
    assert rep_html.status_code == 200
    assert "Laporan Kepatuhan Format Skripsi" in rep_html.text

    # 10. GET /v1/documents/{id}/preview?which=before|after
    prev_before = client.get(f"/v1/documents/{doc_id}/preview?which=before")
    assert prev_before.status_code == 200
    assert prev_before.headers["content-type"] == "application/pdf"
    assert "X-Pagination-Warning" in prev_before.headers
    assert prev_before.content.startswith(b"%PDF-")

    prev_after = client.get(f"/v1/documents/{doc_id}/preview?which=after")
    assert prev_after.status_code == 200
    assert prev_after.content.startswith(b"%PDF-")

    # 11. GET /v1/documents/{id}/download?which=fixed|original
    dl_fixed = client.get(f"/v1/documents/{doc_id}/download?which=fixed")
    assert dl_fixed.status_code == 200
    assert len(dl_fixed.content) > 1000

    dl_orig = client.get(f"/v1/documents/{doc_id}/download?which=original")
    assert dl_orig.status_code == 200
    assert dl_orig.content == src_bytes

    # 12. GET /v1/metrics
    m_res = client.get("/v1/metrics")
    assert m_res.status_code == 200
    assert m_res.json()["total_analyses"] >= 1

    # 13. DELETE /v1/documents/{id}
    del_res = client.delete(f"/v1/documents/{doc_id}")
    assert del_res.status_code == 200


def test_performance_nfr03_100pages():
    reset_rate_limiter()
    fixtures_dir = ensure_all_fixtures()
    large_bytes = (fixtures_dir / "large_100pages.docx").read_bytes()

    up_res = client.post(
        "/v1/documents",
        files={"file": ("large_100pages.docx", large_bytes, "application/octet-stream")},
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["doc_id"]

    t0 = time.perf_counter()
    an_res = client.post(
        f"/v1/documents/{doc_id}/analyze",
        json={"profile_id": "contoh-s1-skripsi"},
    )
    analyze_sec = time.perf_counter() - t0
    assert an_res.status_code == 200
    # NFR-03 target: analyze < 30 seconds
    assert analyze_sec < 30.0, f"Analyze took {analyze_sec:.2f}s (> 30s NFR-03 limit)"

    t1 = time.perf_counter()
    fix_res = client.post(
        f"/v1/documents/{doc_id}/fix",
        json={"profile_id": "contoh-s1-skripsi", "mode": "all"},
    )
    prev_res = client.get(f"/v1/documents/{doc_id}/preview?which=after")
    fix_and_preview_sec = time.perf_counter() - t1
    assert fix_res.status_code == 200
    assert prev_res.status_code == 200
    # NFR-03 target: fix + preview < 90 seconds
    assert fix_and_preview_sec < 90.0

    client.delete(f"/v1/documents/{doc_id}")
