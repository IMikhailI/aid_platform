<script setup>
import PublicLayout from "../../layouts/PublicLayout.vue";
import HeroSection from "../../components/landing/HeroSection.vue";
import AidCategoriesSection from "../../components/landing/AidCategoriesSection.vue";
import RequestExamplesSection from "../../components/landing/RequestExamplesSection.vue";
import HowItWorksSection from "../../components/landing/HowItWorksSection.vue";
import TargetAidSection from "../../components/landing/TargetAidSection.vue";
import FraudProtectionSection from "../../components/landing/FraudProtectionSection.vue";
import FaqSection from "../../components/landing/FaqSection.vue";
</script>

<template>
  <PublicLayout>
    <HeroSection />
    <AidCategoriesSection />
    <RequestExamplesSection />
    <HowItWorksSection />
    <TargetAidSection />
    <FraudProtectionSection />
    <FaqSection />
  </PublicLayout>
</template>
