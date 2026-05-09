from rest_framework import serializers
from fraud.models import FraudCheck, FraudDecision, FraudOverride, FraudAction


class FraudCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudCheck
        fields = ["id", "signal_code", "weight", "value", "created_at"]


class FraudDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudDecision
        fields = [
            "id",
            "score",
            "risk_level",
            "base_action",
            "action",
            "is_overridden",
            "reasons",
            "engine_version",
            "decided_at",
        ]


class FraudOverrideSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source="changed_by.username", read_only=True)

    class Meta:
        model = FraudOverride
        fields = [
            "id",
            "old_action",
            "new_action",
            "comment",
            "changed_by",
            "changed_by_username",
            "created_at",
        ]
        read_only_fields = ["id", "old_action", "changed_by", "created_at"]


class FraudOverrideCreateSerializer(serializers.Serializer):
    new_action = serializers.ChoiceField(choices=FraudAction.choices)
    comment = serializers.CharField()
