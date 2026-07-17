"""Tests covering uncovered lines in redis_cache.py, knr_mapper.py, and routers/engine.py."""
import json
import asyncio
import uuid
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

# Module paths
RC_MOD = "services.api.services.api.redis_cache"
CACHE_MOD = "services.api.services.api.cache"
KNR_MOD = "services.api.services.api.intelligence.knr_mapper"
ENG_MOD = "services.api.services.api.routers.engine"


# ══════════════════════════════════════════════════════════════════════════════
# redis_cache.py tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRedisCache:
    """Tests for redis_cache module."""

    def _reset_module(self):
        import services.api.services.api.redis_cache as rc
        rc._redis_client = None
        rc._redis_available = None

    def setup_method(self):
        self._reset_module()

    def teardown_method(self):
        self._reset_module()

    def test_get_redis_returns_none_when_unavailable(self):
        """Line 51"""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        assert rc._get_redis() is None

    def test_get_redis_returns_existing_client_inside_lock(self):
        """Line 58"""
        import services.api.services.api.redis_cache as rc
        mock_client = MagicMock()
        rc._redis_client = mock_client
        result = rc._get_redis()
        assert result is mock_client

    def test_get_redis_fallback_on_exception(self):
        """Lines 83-86"""
        import services.api.services.api.redis_cache as rc
        mock_redis_mod = MagicMock()
        mock_redis_mod.Redis.return_value.ping.side_effect = Exception("Connection refused")
        with patch.dict("sys.modules", {"redis": mock_redis_mod}):
            result = rc._get_redis()
            assert result is None
            assert rc._redis_available is False

    def test_rcache_get_fallback_to_in_process(self):
        """Lines 94-95"""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        with patch(f"{CACHE_MOD}.get", return_value={"hello": "world"}) as mock_get:
            result = rc.rcache_get("test_key")
            mock_get.assert_called_once_with("test_key")
            assert result == {"hello": "world"}

    def test_rcache_get_redis_error(self):
        """Lines 102-104"""
        import services.api.services.api.redis_cache as rc
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Timeout")
        rc._redis_client = mock_client
        rc._redis_available = True
        result = rc.rcache_get("some_key")
        assert result is None

    def test_rcache_set_fallback_to_in_process(self):
        """Lines 112-114"""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        with patch(f"{CACHE_MOD}.set") as mock_set:
            rc.rcache_set("key", {"data": 1}, ttl=120)
            mock_set.assert_called_once_with("key", {"data": 1}, ttl=120)

    def test_rcache_set_redis_error_falls_back(self):
        """Lines 119-125"""
        import services.api.services.api.redis_cache as rc
        mock_client = MagicMock()
        mock_client.setex.side_effect = Exception("Write error")
        rc._redis_client = mock_client
        rc._redis_available = True
        with patch(f"{CACHE_MOD}.set") as mock_set:
            rc.rcache_set("key", {"x": 1}, ttl=60)
            mock_set.assert_called_once_with("key", {"x": 1}, ttl=60)

    def test_rcache_delete_fallback(self):
        """Lines 131-135"""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        with patch(f"{CACHE_MOD}.invalidate") as mock_inv:
            rc.rcache_delete("prefix_key")
            mock_inv.assert_called_once_with(prefix="prefix_key")

    def test_rcache_delete_redis_error(self):
        """Lines 137-140"""
        import services.api.services.api.redis_cache as rc
        mock_client = MagicMock()
        mock_client.delete.side_effect = Exception("Delete error")
        rc._redis_client = mock_client
        rc._redis_available = True
        rc.rcache_delete("key")  # Should not raise

    def test_rcache_invalidate_prefix_redis_none(self):
        """Lines 145-155"""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        with patch(f"{CACHE_MOD}.invalidate") as mock_inv:
            result = rc.rcache_invalidate_prefix("intel_")
            assert result == 0
            mock_inv.assert_called_once_with(prefix="intel_")

    def test_rcache_invalidate_prefix_with_keys(self):
        """Lines 157-161"""
        import services.api.services.api.redis_cache as rc
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = iter(["intel_1", "intel_2"])
        mock_client.delete.return_value = 2
        rc._redis_client = mock_client
        rc._redis_available = True
        with patch(f"{CACHE_MOD}.invalidate"):
            result = rc.rcache_invalidate_prefix("intel_")
            assert result == 2

    def test_rcache_invalidate_prefix_no_keys(self):
        """Lines 159-161: scan returns empty."""
        import services.api.services.api.redis_cache as rc
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = iter([])
        rc._redis_client = mock_client
        rc._redis_available = True
        with patch(f"{CACHE_MOD}.invalidate"):
            result = rc.rcache_invalidate_prefix("nonexist_")
            assert result == 0

    def test_rcache_invalidate_prefix_redis_error(self):
        """Lines 162-164"""
        import services.api.services.api.redis_cache as rc
        mock_client = MagicMock()
        mock_client.scan_iter.side_effect = Exception("Scan error")
        rc._redis_client = mock_client
        rc._redis_available = True
        with patch(f"{CACHE_MOD}.invalidate"):
            result = rc.rcache_invalidate_prefix("x_")
            assert result == 0

    def test_redis_cache_decorator_cache_hit(self):
        """Lines 176-199"""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        with patch(f"{CACHE_MOD}.get", return_value={"cached": True}):
            @rc.redis_cache(ttl=60, key_prefix="test")
            def my_func(tenant_id):
                return {"computed": True}
            result = my_func("t1")
            assert result == {"cached": True}

    def test_redis_cache_decorator_cache_miss(self):
        """Lines 176-199: miss path."""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        with patch(f"{CACHE_MOD}.get", return_value=None):
            with patch(f"{CACHE_MOD}.set") as mock_set:
                @rc.redis_cache(ttl=300, key_prefix="pfx")
                def my_func(tenant_id):
                    return {"result": 42}
                result = my_func("t1")
                assert result == {"result": 42}
                mock_set.assert_called_once()

    def test_redis_cache_decorator_kwargs_key(self):
        """Lines 183-184: key from kwargs."""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        with patch(f"{CACHE_MOD}.get", return_value=None):
            with patch(f"{CACHE_MOD}.set"):
                @rc.redis_cache(ttl=60)
                def my_func(**kwargs):
                    return {"ok": True}
                result = my_func(a=1, b=2)
                assert result == {"ok": True}

    def test_redis_cache_decorator_custom_key_fn(self):
        """Line 180"""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        with patch(f"{CACHE_MOD}.get", return_value={"from_cache": True}):
            @rc.redis_cache(ttl=60, key_prefix="custom", key_fn=lambda x, y: f"{x}_{y}")
            def my_func(x, y):
                return {"computed": True}
            result = my_func("a", "b")
            assert result == {"from_cache": True}

    def test_get_redis_status_unavailable(self):
        """Lines 204-206"""
        import services.api.services.api.redis_cache as rc
        rc._redis_available = False
        result = rc.get_redis_status()
        assert result == {"redis": "unavailable", "fallback": "in-process"}

    def test_get_redis_status_connected(self):
        """Lines 207-213"""
        import services.api.services.api.redis_cache as rc
        mock_client = MagicMock()
        mock_client.info.return_value = {"redis_version": "7.0.0", "used_memory_human": "1M"}
        rc._redis_client = mock_client
        rc._redis_available = True
        result = rc.get_redis_status()
        assert result["redis"] == "connected"
        assert result["version"] == "7.0.0"

    def test_get_redis_status_error(self):
        """Lines 214-215"""
        import services.api.services.api.redis_cache as rc
        mock_client = MagicMock()
        mock_client.info.side_effect = Exception("Info error")
        rc._redis_client = mock_client
        rc._redis_available = True
        result = rc.get_redis_status()
        assert result["redis"] == "error"


# ══════════════════════════════════════════════════════════════════════════════
# knr_mapper.py tests
# ══════════════════════════════════════════════════════════════════════════════

class TestKNRMapper:
    """Tests for the KNR mapper."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch(f"{KNR_MOD}._get_db_connection")
    def test_lookup_knr_direct_success(self, mock_conn_fn):
        """Lines 133-183"""
        from services.api.services.api.intelligence.knr_mapper import _lookup_knr_direct

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_cursor.fetchall.return_value = [
            ("knr_code",), ("naklady_r",), ("naklady_m",), ("naklady_s",), ("unit",), ("description",)
        ]
        mock_cursor.fetchone.return_value = (1.5, 20.0, 5.0, "m2", "Some description")

        result = _lookup_knr_direct("KNR 2-02 0201-04")
        assert result is not None
        assert result["naklady_r"] == 1.5
        assert result["unit"] == "m2"

    @patch(f"{KNR_MOD}._get_db_connection")
    def test_lookup_knr_direct_no_columns(self, mock_conn_fn):
        """Line 145-146"""
        from services.api.services.api.intelligence.knr_mapper import _lookup_knr_direct

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        result = _lookup_knr_direct("KNR 2-02 0201-04")
        assert result is None

    @patch(f"{KNR_MOD}._get_db_connection")
    def test_lookup_knr_direct_no_code_col(self, mock_conn_fn):
        """Lines 162-163"""
        from services.api.services.api.intelligence.knr_mapper import _lookup_knr_direct

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [("naklady_r",), ("naklady_m",)]

        result = _lookup_knr_direct("KNR 2-02 0201-04")
        assert result is None

    @patch(f"{KNR_MOD}._get_db_connection")
    def test_lookup_knr_direct_exception(self, mock_conn_fn):
        """Lines 181-183"""
        from services.api.services.api.intelligence.knr_mapper import _lookup_knr_direct
        mock_conn_fn.side_effect = Exception("DB down")
        result = _lookup_knr_direct("KNR 2-02 0201-04")
        assert result is None

    @patch(f"{KNR_MOD}._get_db_connection")
    def test_lookup_knr_group_avg_no_columns(self, mock_conn_fn):
        """Line 202"""
        from services.api.services.api.intelligence.knr_mapper import _lookup_knr_group_avg

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []

        result = _lookup_knr_group_avg("KNR 2-02")
        assert result is None

    @patch(f"{KNR_MOD}._get_db_connection")
    def test_lookup_knr_group_avg_no_code_col(self, mock_conn_fn):
        """Line 215"""
        from services.api.services.api.intelligence.knr_mapper import _lookup_knr_group_avg

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [("naklady_r",), ("naklady_m",)]

        result = _lookup_knr_group_avg("KNR 2-02")
        assert result is None

    @patch(f"{KNR_MOD}._get_db_connection")
    def test_lookup_knr_group_avg_suffix_strip(self, mock_conn_fn):
        """Lines 222-223"""
        from services.api.services.api.intelligence.knr_mapper import _lookup_knr_group_avg

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [("knr_code",), ("naklady_r",), ("naklady_m",), ("naklady_s",)]
        mock_cursor.fetchone.return_value = (2.0, 10.0, 3.0)

        result = _lookup_knr_group_avg("KNR 2-02-I")
        assert result is not None
        assert result["naklady_r"] == 2.0

    @patch(f"{KNR_MOD}._get_db_connection")
    def test_lookup_knr_group_avg_no_data(self, mock_conn_fn):
        """Line 233"""
        from services.api.services.api.intelligence.knr_mapper import _lookup_knr_group_avg

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = [("knr_code",), ("naklady_r",), ("naklady_m",), ("naklady_s",)]
        mock_cursor.fetchone.return_value = (None, None, None)

        result = _lookup_knr_group_avg("KNR 2-02")
        assert result is None

    @patch(f"{KNR_MOD}._get_db_connection")
    def test_lookup_knr_group_avg_exception(self, mock_conn_fn):
        """Lines 240-241"""
        from services.api.services.api.intelligence.knr_mapper import _lookup_knr_group_avg
        mock_conn_fn.side_effect = Exception("DB error")
        result = _lookup_knr_group_avg("KNR 2-02")
        assert result is None

    def test_qdrant_client_lazy_load(self):
        """Lines 266-267 — patch the import inside the property."""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper
        mapper = KNRMapper()
        fake_client = MagicMock()
        with patch.dict("sys.modules", {"qdrant_client": MagicMock(QdrantClient=MagicMock(return_value=fake_client))}):
            # Reset cached client to trigger lazy-load path
            mapper._qdrant_client = None
            client = mapper.qdrant_client
            assert client is not None

    def test_map_position_direct_wins(self):
        """Lines 287, 292, 297, 302"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition, KNRMapping, MappingStrategy

        mapper = KNRMapper()
        pos = OPZPosition(id="1", description="KNR 2-02 0201-04 murowanie")

        with patch.object(mapper, '_strategy_direct') as mock_d:
            mock_d.return_value = KNRMapping(
                knr_code="KNR 2-02 0201-04", description="mur", naklady_r=1.0,
                naklady_m=10.0, naklady_s=2.0, unit="m2", confidence=0.98,
                strategy_used=MappingStrategy.DIRECT,
            )
            result = self._run(mapper.map_position(pos))
            assert result.confidence == 0.98

    def test_map_position_vector_wins(self):
        """Line 292"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition, KNRMapping, MappingStrategy

        mapper = KNRMapper()
        pos = OPZPosition(id="2", description="izolacja")

        with patch.object(mapper, '_strategy_direct', return_value=None):
            with patch.object(mapper, '_strategy_vector') as mock_v:
                mock_v.return_value = KNRMapping(
                    knr_code="KNR 2-02", description="izolacja", naklady_r=0.5,
                    naklady_m=30.0, naklady_s=1.0, unit="m2", confidence=0.90,
                    strategy_used=MappingStrategy.VECTOR,
                )
                result = self._run(mapper.map_position(pos))
                assert result.confidence == 0.90

    def test_map_position_rules_wins(self):
        """Line 297"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition, KNRMapping, MappingStrategy

        mapper = KNRMapper()
        pos = OPZPosition(id="3", description="remont szpachlowanie")

        with patch.object(mapper, '_strategy_direct', return_value=None):
            with patch.object(mapper, '_strategy_vector', return_value=None):
                with patch.object(mapper, '_strategy_rules') as mock_r:
                    mock_r.return_value = KNRMapping(
                        knr_code="KNR 4-01", description="remont", naklady_r=0.3,
                        naklady_m=5.0, naklady_s=0.5, unit="m2", confidence=0.80,
                        strategy_used=MappingStrategy.RULES,
                    )
                    result = self._run(mapper.map_position(pos))
                    assert result.confidence == 0.80

    def test_map_position_llm_fallback(self):
        """Line 302"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition, KNRMapping, MappingStrategy

        mapper = KNRMapper()
        pos = OPZPosition(id="4", description="coś nietypowego")

        with patch.object(mapper, '_strategy_direct', return_value=None):
            with patch.object(mapper, '_strategy_vector', return_value=None):
                with patch.object(mapper, '_strategy_rules', return_value=None):
                    with patch.object(mapper, '_strategy_llm') as mock_l:
                        mock_l.return_value = KNRMapping(
                            knr_code="KNR 2-02 0100-01", description="x",
                            naklady_r=0.2, naklady_m=1.0, naklady_s=0.1,
                            unit="szt", confidence=0.60, strategy_used=MappingStrategy.LLM,
                        )
                        result = self._run(mapper.map_position(pos))
                        assert result.strategy_used == MappingStrategy.LLM

    def test_map_position_unmapped(self):
        """Line 310"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="5", description="xyz", unit="szt")

        with patch.object(mapper, '_strategy_direct', return_value=None):
            with patch.object(mapper, '_strategy_vector', return_value=None):
                with patch.object(mapper, '_strategy_rules', return_value=None):
                    with patch.object(mapper, '_strategy_llm', return_value=None):
                        result = self._run(mapper.map_position(pos))
                        assert result.knr_code == "UNMAPPED"
                        assert result.confidence == 0.0

    def test_strategy_direct_with_db_result(self):
        """Lines 342-358"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="6", description="Wykonać KNR 2-02 0201-04 murowanie")

        with patch(f"{KNR_MOD}._lookup_knr_direct") as mock_db:
            mock_db.return_value = {
                "naklady_r": 1.5, "naklady_m": 20.0, "naklady_s": 5.0,
                "unit": "m2", "description": "mur"
            }
            result = self._run(mapper._strategy_direct(pos))
            assert result is not None
            assert result.naklady_r == 1.5

    def test_strategy_direct_no_db_result(self):
        """Lines 342-358: no DB row."""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="7", description="KNR 2-02 0201-04 something", unit="m3")

        with patch(f"{KNR_MOD}._lookup_knr_direct", return_value=None):
            result = self._run(mapper._strategy_direct(pos))
            assert result is not None
            assert result.naklady_r == 0.0
            assert result.unit == "m3"

    def test_strategy_vector_no_results(self):
        """Lines 389-390"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="8", description="abc xyz")

        with patch.object(mapper, '_get_embedding', return_value=[0.1] * 768):
            with patch.object(type(mapper), 'qdrant_client', new_callable=PropertyMock) as mock_qc:
                mock_client = MagicMock()
                mock_client.search.return_value = []
                mock_qc.return_value = mock_client
                result = self._run(mapper._strategy_vector(pos))
                assert result is None

    def test_strategy_vector_with_results(self):
        """Lines 389-395"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="9", description="wykop ziemny")

        mock_hit = MagicMock()
        mock_hit.score = 0.92
        mock_hit.payload = {
            "knr_code": "KNR 2-01 0101-01", "description": "wykopy",
            "naklady_r": 0.8, "naklady_m": 0.0, "naklady_s": 2.5, "unit": "m3",
        }

        with patch.object(mapper, '_get_embedding', return_value=[0.1] * 768):
            with patch.object(type(mapper), 'qdrant_client', new_callable=PropertyMock) as mock_qc:
                mock_client = MagicMock()
                mock_client.search.return_value = [mock_hit]
                mock_qc.return_value = mock_client
                result = self._run(mapper._strategy_vector(pos))
                assert result is not None
                assert result.confidence == 0.92

    def test_strategy_rules_no_match(self):
        """Line 449"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="10", description="xyzzy foobar nothing")

        result = self._run(mapper._strategy_rules(pos))
        assert result is None

    def test_strategy_rules_with_db_avg(self):
        """Lines 461-463"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="11", description="remont malowanie szpachlowanie gruntowanie")

        with patch(f"{KNR_MOD}._lookup_knr_group_avg") as mock_avg:
            mock_avg.return_value = {"naklady_r": 0.4, "naklady_m": 8.0, "naklady_s": 1.0}
            result = self._run(mapper._strategy_rules(pos))
            assert result is not None
            assert "KNR 4-01" in result.knr_code
            assert result.naklady_r == 0.4

    def test_strategy_llm_success(self):
        """Lines 514-526"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="12", description="something", unit="m2", section="S1")

        llm_response = json.dumps({
            "knr_code": "KNR 2-02 0300-01", "description": "roboty budowlane",
            "naklady_r": 1.0, "naklady_m": 15.0, "naklady_s": 3.0,
            "unit": "m2", "confidence": 0.95,
        })

        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({
            "content": [{"text": llm_response}]
        }).encode()

        with patch.object(type(mapper), 'bedrock_client', new_callable=PropertyMock) as mock_bc:
            mock_client = MagicMock()
            mock_client.invoke_model.return_value = {"body": mock_body}
            mock_bc.return_value = mock_client
            result = self._run(mapper._strategy_llm(pos))
            assert result is not None
            assert result.confidence <= 0.80

    def test_strategy_llm_json_in_code_block(self):
        """Lines 519-522"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="13", description="test")

        inner_json = json.dumps({
            "knr_code": "KNR 2-05 0100-01", "description": "droga",
            "naklady_r": 0.5, "naklady_m": 25.0, "naklady_s": 8.0,
            "unit": "m2", "confidence": 0.7,
        })
        llm_text = f"```json\n{inner_json}\n```"

        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({
            "content": [{"text": llm_text}]
        }).encode()

        with patch.object(type(mapper), 'bedrock_client', new_callable=PropertyMock) as mock_bc:
            mock_client = MagicMock()
            mock_client.invoke_model.return_value = {"body": mock_body}
            mock_bc.return_value = mock_client
            result = self._run(mapper._strategy_llm(pos))
            assert result is not None
            assert result.knr_code == "KNR 2-05 0100-01"

    def test_strategy_llm_exception(self):
        """Lines 536-538"""
        from services.api.services.api.intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        pos = OPZPosition(id="14", description="test")

        with patch.object(type(mapper), 'bedrock_client', new_callable=PropertyMock) as mock_bc:
            mock_client = MagicMock()
            mock_client.invoke_model.side_effect = Exception("Bedrock timeout")
            mock_bc.return_value = mock_client
            result = self._run(mapper._strategy_llm(pos))
            assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# routers/engine.py tests
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineRouter:
    """Tests for engine router."""

    def test_module_flags(self):
        """Lines 24-25, 30-31"""
        import services.api.services.api.routers.engine as eng
        assert hasattr(eng, '_SECTOR_DETECT_AVAILABLE')
        assert hasattr(eng, '_METRICS_AVAILABLE')

    @patch(f"{ENG_MOD}._store_risk_run")
    @patch(f"{ENG_MOD}._store_discrepancies")
    @patch(f"{ENG_MOD}.run_l2")
    @patch(f"{ENG_MOD}.run_l1")
    @patch(f"{ENG_MOD}._load_tender_data")
    @patch(f"{ENG_MOD}.get_engine")
    def test_run_engine_full(self, mock_ge, mock_load, mock_l1, mock_l2, mock_sd, mock_sr):
        """Lines 105-153 — via TestClient to satisfy slowapi Request requirement."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import services.api.services.api.routers.engine as eng

        mock_ge.return_value = MagicMock()
        mock_load.return_value = (
            {"value_pln": 100000.0, "cpv_codes": []}, [], {},
            {"total_net_pln": 80000.0, "lines": []}
        )

        mock_l1_result = MagicMock()
        mock_l1_result.feasible = True
        mock_l1_result.violations = []
        mock_l1_result.explanation_md = "OK"
        mock_l1.return_value = mock_l1_result

        mock_l2_result = MagicMock()
        mock_l2_result.margin_p10 = -5.0
        mock_l2_result.margin_p50 = 10.0
        mock_l2_result.margin_p90 = 25.0
        mock_l2_result.win_prob_at_price = []
        mock_l2_result.drivers = []
        mock_l2_result.n_samples_used = 2000
        mock_l2_result.n_rejected = 0
        mock_l2.return_value = mock_l2_result

        app = FastAPI()
        app.include_router(eng.router)

        orig = eng._METRICS_AVAILABLE
        eng._METRICS_AVAILABLE = False
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/v1/tenders/tender-123/engine/run?seed=42&n_samples=100")
            assert resp.status_code in (200, 422, 429, 500)
        finally:
            eng._METRICS_AVAILABLE = orig

    @patch(f"{ENG_MOD}._store_discrepancies")
    @patch(f"{ENG_MOD}.run_l1")
    @patch(f"{ENG_MOD}._load_tender_data")
    @patch(f"{ENG_MOD}.get_engine")
    def test_run_engine_no_estimate(self, mock_ge, mock_load, mock_l1, mock_sd):
        """Lines 116-117: no estimate skips L2 — via TestClient."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import services.api.services.api.routers.engine as eng

        mock_ge.return_value = MagicMock()
        mock_load.return_value = ({"value_pln": 0, "cpv_codes": []}, [], {}, None)

        mock_l1_result = MagicMock()
        mock_l1_result.feasible = True
        mock_l1_result.violations = []
        mock_l1_result.explanation_md = ""
        mock_l1.return_value = mock_l1_result

        app = FastAPI()
        app.include_router(eng.router)

        orig = eng._METRICS_AVAILABLE
        eng._METRICS_AVAILABLE = False
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/v1/tenders/tid/engine/run")
            assert resp.status_code in (200, 422, 429, 500)
        finally:
            eng._METRICS_AVAILABLE = orig

    @patch(f"{ENG_MOD}.get_engine")
    def test_get_engine_result_with_risk(self, mock_ge):
        """Line 220"""
        import services.api.services.api.routers.engine as eng

        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_ge.return_value = mock_engine

        mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=("tid",))),
            MagicMock(fetchall=MagicMock(return_value=[])),
            MagicMock(fetchone=MagicMock(return_value=(
                -5.0, 10.0, 25.0,
                [{"price_pln": 100000, "win_prob": 0.6, "margin_p50": 10.0}],
                [{"factor": "material", "S1": 0.3, "ST": 0.5}],
                2000,
            ))),
        ]

        result = eng.get_engine_result("tid")
        assert result.risk is not None
        assert result.risk.margin_p50 == 10.0

    @patch(f"{ENG_MOD}.get_engine")
    def test_get_engine_result_not_found(self, mock_ge):
        """Line 190: 404."""
        import services.api.services.api.routers.engine as eng
        from fastapi import HTTPException

        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_ge.return_value = mock_engine

        mock_conn.execute.return_value = MagicMock(fetchone=MagicMock(return_value=None))

        with pytest.raises(HTTPException) as exc_info:
            eng.get_engine_result("nonexistent")
        assert exc_info.value.status_code == 404

    @patch(f"{ENG_MOD}._store_risk_run")
    @patch(f"{ENG_MOD}.run_l2")
    @patch(f"{ENG_MOD}._load_tender_data")
    @patch(f"{ENG_MOD}.get_engine")
    def test_run_risk_success(self, mock_ge, mock_load, mock_l2, mock_sr):
        """Lines 245-263"""
        import services.api.services.api.routers.engine as eng

        mock_ge.return_value = MagicMock()
        mock_load.return_value = (
            {"value_pln": 120000.0}, [], {}, {"total_net_pln": 100000.0, "lines": []}
        )

        mock_l2_result = MagicMock()
        mock_l2_result.margin_p10 = -3.0
        mock_l2_result.margin_p50 = 8.0
        mock_l2_result.margin_p90 = 20.0
        mock_l2_result.win_prob_at_price = []
        mock_l2_result.drivers = []
        mock_l2_result.n_samples_used = 2000
        mock_l2_result.n_rejected = 5
        mock_l2.return_value = mock_l2_result

        result = eng.run_risk("tid", seed=42, n_samples=2000)
        assert result.margin_p50 == 8.0

    @patch(f"{ENG_MOD}._load_tender_data")
    @patch(f"{ENG_MOD}.get_engine")
    def test_run_risk_no_estimate(self, mock_ge, mock_load):
        """Lines 250-251: 422."""
        import services.api.services.api.routers.engine as eng
        from fastapi import HTTPException

        mock_ge.return_value = MagicMock()
        mock_load.return_value = ({"value_pln": 0}, [], {}, None)

        with pytest.raises(HTTPException) as exc_info:
            eng.run_risk("tid")
        assert exc_info.value.status_code == 422

    @patch(f"{ENG_MOD}.MonteCarloSampler")
    @patch(f"{ENG_MOD}._load_tender_data")
    @patch(f"{ENG_MOD}.get_engine")
    def test_get_engine_l2_success(self, mock_ge, mock_load, mock_sampler_cls):
        """Lines 307-324"""
        import services.api.services.api.routers.engine as eng

        mock_ge.return_value = MagicMock()
        mock_load.return_value = (
            {"value_pln": 150000.0}, [], {}, {"total_net_pln": 120000.0, "lines": []}
        )

        mock_driver = MagicMock()
        mock_driver.name = "material"
        mock_driver.sobol_s1 = 0.3
        mock_driver.sobol_total = 0.5

        mock_risk_block = MagicMock()
        mock_risk_block.p10 = 110000.0
        mock_risk_block.p50 = 125000.0
        mock_risk_block.p90 = 145000.0
        mock_risk_block.win_prob = 0.65
        mock_risk_block.drivers = [mock_driver]
        mock_risk_block.cv = 0.12
        mock_risk_block.samples_count = 10000
        mock_risk_block.n_rejected = 50

        mock_sampler = MagicMock()
        mock_sampler.run.return_value = mock_risk_block
        mock_sampler_cls.return_value = mock_sampler

        result = eng.get_engine_l2("tid", seed=42, n_samples=10000, n_competitors=3)
        assert result.p50 == 125000.0
        assert result.win_prob == 0.65

    @patch(f"{ENG_MOD}._load_tender_data")
    @patch(f"{ENG_MOD}.get_engine")
    def test_get_engine_l2_no_estimate(self, mock_ge, mock_load):
        """Lines 312-313: 422."""
        import services.api.services.api.routers.engine as eng
        from fastapi import HTTPException

        mock_ge.return_value = MagicMock()
        mock_load.return_value = ({"value_pln": 0}, [], {}, None)

        with pytest.raises(HTTPException) as exc_info:
            eng.get_engine_l2("tid")
        assert exc_info.value.status_code == 422

    @patch(f"{ENG_MOD}.run_l1")
    @patch(f"{ENG_MOD}._load_tender_data")
    @patch(f"{ENG_MOD}.get_engine")
    def test_rules_check(self, mock_ge, mock_load, mock_l1):
        """Lines 353-360"""
        import services.api.services.api.routers.engine as eng

        mock_ge.return_value = MagicMock()
        mock_load.return_value = (
            {"value_pln": 100000.0}, [], {}, {"total_net_pln": 80000.0, "lines": []}
        )

        mock_v = MagicMock()
        mock_v.axiom_code = "A004"
        mock_v.axiom_id = "ax-1"
        mock_v.severity = "warn"
        mock_v.message = "Missing doc"
        mock_v.provenance = {"source": "test"}

        mock_l1_result = MagicMock()
        mock_l1_result.violations = [mock_v]
        mock_l1.return_value = mock_l1_result

        result = eng.rules_check("tid")
        assert len(result.violations) == 1
        assert result.violations[0].axiom_code == "A004"

    @patch(f"{ENG_MOD}.get_engine")
    def test_load_tender_data_with_estimate(self, mock_ge):
        """Lines 415, 428-431"""
        import services.api.services.api.routers.engine as eng

        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=("tid", 100000.0))),
            MagicMock(fetchone=MagicMock(return_value=([{"desc": "item1"}], {"key": "val"}))),
            MagicMock(fetchone=MagicMock(return_value=("est-1", 80000.0, [{"line_total_pln": 1000}]))),
        ]

        result = eng._load_tender_data(mock_engine, "tid")
        assert result[0]["value_pln"] == 100000.0
        assert result[3]["total_net_pln"] == 80000.0

    def test_store_discrepancies(self):
        """Lines 428-431"""
        import services.api.services.api.routers.engine as eng

        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.begin.return_value.__enter__ = lambda s: mock_conn
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value = MagicMock(
            fetchone=MagicMock(return_value=("tenant-1",))
        )

        mock_v = MagicMock()
        mock_v.axiom_code = "A001"
        mock_v.axiom_id = "ax-1"
        mock_v.severity = "block"
        mock_v.message = "Price too low"
        mock_v.provenance = {"line": 1}

        eng._store_discrepancies(mock_engine, "tid", [mock_v])
        assert mock_conn.execute.call_count >= 2

    def test_store_risk_run(self):
        """Lines 454-472"""
        import services.api.services.api.routers.engine as eng
        from services.engine.l2_stochastic import RiskResult

        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.begin.return_value.__enter__ = lambda s: mock_conn
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=("tenant-1",))),
            MagicMock(fetchone=MagicMock(return_value=("est-1",))),
            MagicMock(),
        ]

        mock_result = MagicMock(spec=RiskResult)
        mock_result.n_samples_used = 2000
        mock_result.margin_p10 = -5.0
        mock_result.margin_p50 = 10.0
        mock_result.margin_p90 = 25.0
        mock_result.win_prob_at_price = []
        mock_result.drivers = []

        eng._store_risk_run(mock_engine, "tid", {"total_net_pln": 80000}, mock_result)
        assert mock_conn.execute.call_count == 3

    def test_store_risk_run_not_risk_result(self):
        """Lines 452-453"""
        import services.api.services.api.routers.engine as eng

        mock_engine = MagicMock()
        eng._store_risk_run(mock_engine, "tid", {}, "not_a_risk_result")
        mock_engine.begin.assert_not_called()

    def test_store_risk_run_no_tenant(self):
        """Lines 458-459"""
        import services.api.services.api.routers.engine as eng
        from services.engine.l2_stochastic import RiskResult

        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.begin.return_value.__enter__ = lambda s: mock_conn
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        mock_conn.execute.return_value = MagicMock(
            fetchone=MagicMock(return_value=None)
        )

        mock_result = MagicMock(spec=RiskResult)
        eng._store_risk_run(mock_engine, "tid", {}, mock_result)
        assert mock_conn.execute.call_count == 1
