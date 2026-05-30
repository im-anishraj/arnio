"""Tests for UUID and IPAddress schema field validators."""

import pandas as pd
import pytest

import arnio as ar


class TestUUIDValidation:
    def test_uuid_accepts_valid_uuids(self):
        schema = ar.Schema(
            {
                "uuid_col": ar.UUID(),
            }
        )

        df = pd.DataFrame(
            {
                "uuid_col": [
                    "2806ccba-5b12-11ed-9b6a-0242ac120002",  # UUIDv1
                    "6ba7b810-9dad-11d1-80b4-00c04fd430c8",  # UUIDv1
                    "a22b781a-bb0a-4299-b13c-d2c1c2898edd",  # UUIDv4
                    "00000000-0000-0000-0000-000000000000",  # Nil UUID
                ]
            }
        )

        frame = ar.from_pandas(df)
        result = ar.validate(frame, schema)
        assert result.passed
        assert result.issue_count == 0

    def test_uuid_rejects_invalid_formats(self):
        schema = ar.Schema(
            {
                "uuid_col": ar.UUID(),
            }
        )

        df = pd.DataFrame(
            {
                "uuid_col": [
                    "not-a-uuid",
                    "2806ccba-5b12-11ed-9b6a",
                    "g22b781a-bb0a-4299-b13c-d2c1c2898edd",  # 'g' is invalid hex
                    "a22b781a-bb0a-4299-b13c-d2c1c2898edd-extra",
                ]
            }
        )

        frame = ar.from_pandas(df)
        result = ar.validate(frame, schema)
        assert not result.passed
        assert result.issue_count == 4
        assert all(issue.rule == "uuid" for issue in result.issues)

    def test_uuid_strict_version_constraints(self):
        # Strictly UUIDv4
        schema = ar.Schema(
            {
                "uuid4_col": ar.UUID(version=4),
            }
        )

        df = pd.DataFrame(
            {
                "uuid4_col": [
                    "a22b781a-bb0a-4299-b13c-d2c1c2898edd",  # UUIDv4 (valid)
                    "2806ccba-5b12-11ed-9b6a-0242ac120002",  # UUIDv1 (invalid for strict version 4)
                ]
            }
        )

        frame = ar.from_pandas(df)
        result = ar.validate(frame, schema)
        assert not result.passed
        assert result.issue_count == 1
        assert result.issues[0].value == "2806ccba-5b12-11ed-9b6a-0242ac120002"
        assert result.issues[0].rule == "uuid:4"

    def test_uuid_invalid_version_raises(self):
        with pytest.raises(ValueError, match="UUID version must be one of"):
            ar.UUID(version=6)

    def test_uuid_nullable_behavior(self):
        schema = ar.Schema(
            {
                "uuid_col": ar.UUID(nullable=True),
            }
        )

        df = pd.DataFrame(
            {
                "uuid_col": [
                    "a22b781a-bb0a-4299-b13c-d2c1c2898edd",
                    None,
                    pd.NA,
                ]
            }
        )

        frame = ar.from_pandas(df)
        result = ar.validate(frame, schema)
        assert result.passed

    def test_uuid_uniqueness_behavior(self):
        schema = ar.Schema(
            {
                "uuid_col": ar.UUID(unique=True),
            }
        )

        df = pd.DataFrame(
            {
                "uuid_col": [
                    "a22b781a-bb0a-4299-b13c-d2c1c2898edd",
                    "a22b781a-bb0a-4299-b13c-d2c1c2898edd",
                ]
            }
        )

        frame = ar.from_pandas(df)
        result = ar.validate(frame, schema)
        assert not result.passed
        assert any(issue.rule == "unique" for issue in result.issues)

    def test_uuid_invalid_raw_semantic_raises(self):
        # Setting semantic="uuid:foo" directly on Field
        field = ar.Field(dtype="string", semantic="uuid:foo")
        schema = ar.Schema({"uuid_col": field})
        df = pd.DataFrame({"uuid_col": ["a22b781a-bb0a-4299-b13c-d2c1c2898edd"]})
        frame = ar.from_pandas(df)
        with pytest.raises(ValueError, match="Invalid UUID version suffix in semantic"):
            ar.validate(frame, schema)

        # Setting semantic="uuid:6" directly on Field
        field2 = ar.Field(dtype="string", semantic="uuid:6")
        schema2 = ar.Schema({"uuid_col": field2})
        with pytest.raises(ValueError, match="UUID version must be one of"):
            ar.validate(frame, schema2)


class TestIPAddressValidation:
    def test_ip_accepts_valid_ipv4_and_ipv6(self):
        schema = ar.Schema(
            {
                "ip_col": ar.IPAddress(),
            }
        )

        df = pd.DataFrame(
            {
                "ip_col": [
                    "192.168.1.1",
                    "8.8.8.8",
                    "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                    "fe80::1",
                    "::1",
                ]
            }
        )

        frame = ar.from_pandas(df)
        result = ar.validate(frame, schema)
        assert result.passed
        assert result.issue_count == 0

    def test_ip_rejects_invalid_formats(self):
        schema = ar.Schema(
            {
                "ip_col": ar.IPAddress(),
            }
        )

        df = pd.DataFrame(
            {
                "ip_col": [
                    "256.0.0.1",  # Octet > 255
                    "192.168.1.1.1",  # Too many octets
                    "2001:xyz::1",  # Invalid characters for IPv6
                    "not-an-ip",
                    "123.456",
                ]
            }
        )

        frame = ar.from_pandas(df)
        result = ar.validate(frame, schema)
        assert not result.passed
        assert result.issue_count == 5
        assert all(issue.rule == "ip_address" for issue in result.issues)

    def test_ip_strict_version_constraints(self):
        # Strict IPv4
        schema_v4 = ar.Schema(
            {
                "ipv4_col": ar.IPAddress(version=4),
            }
        )

        df_v4 = pd.DataFrame(
            {
                "ipv4_col": [
                    "192.168.1.1",  # IPv4
                    "2001:db8::1",  # IPv6 (invalid under strict version 4)
                ]
            }
        )

        frame_v4 = ar.from_pandas(df_v4)
        result_v4 = ar.validate(frame_v4, schema_v4)
        assert not result_v4.passed
        assert result_v4.issue_count == 1
        assert result_v4.issues[0].value == "2001:db8::1"
        assert result_v4.issues[0].rule == "ip_address:4"

        # Strict IPv6
        schema_v6 = ar.Schema(
            {
                "ipv6_col": ar.IPAddress(version=6),
            }
        )

        df_v6 = pd.DataFrame(
            {
                "ipv6_col": [
                    "2001:db8::1",  # IPv6
                    "192.168.1.1",  # IPv4 (invalid under strict version 6)
                ]
            }
        )

        frame_v6 = ar.from_pandas(df_v6)
        result_v6 = ar.validate(frame_v6, schema_v6)
        assert not result_v6.passed
        assert result_v6.issue_count == 1
        assert result_v6.issues[0].value == "192.168.1.1"
        assert result_v6.issues[0].rule == "ip_address:6"

    def test_ip_invalid_version_raises(self):
        with pytest.raises(ValueError, match="IPAddress version must be 4 or 6"):
            ar.IPAddress(version=5)

    def test_ip_nullable_behavior(self):
        schema = ar.Schema(
            {
                "ip_col": ar.IPAddress(nullable=True),
            }
        )

        df = pd.DataFrame(
            {
                "ip_col": [
                    "8.8.8.8",
                    None,
                    pd.NA,
                ]
            }
        )

        frame = ar.from_pandas(df)
        result = ar.validate(frame, schema)
        assert result.passed

    def test_ip_uniqueness_behavior(self):
        schema = ar.Schema(
            {
                "ip_col": ar.IPAddress(unique=True),
            }
        )

        df = pd.DataFrame(
            {
                "ip_col": [
                    "8.8.8.8",
                    "8.8.8.8",
                ]
            }
        )

        frame = ar.from_pandas(df)
        result = ar.validate(frame, schema)
        assert not result.passed
        assert any(issue.rule == "unique" for issue in result.issues)

    def test_ip_invalid_raw_semantic_raises(self):
        # Setting semantic="ip_address:bar" directly on Field
        field = ar.Field(dtype="string", semantic="ip_address:bar")
        schema = ar.Schema({"ip_col": field})
        df = pd.DataFrame({"ip_col": ["192.168.1.1"]})
        frame = ar.from_pandas(df)
        with pytest.raises(
            ValueError, match="Invalid IPAddress version suffix in semantic"
        ):
            ar.validate(frame, schema)

        # Setting semantic="ip_address:5" directly on Field
        field2 = ar.Field(dtype="string", semantic="ip_address:5")
        schema2 = ar.Schema({"ip_col": field2})
        with pytest.raises(ValueError, match="IPAddress version must be 4 or 6"):
            ar.validate(frame, schema2)
