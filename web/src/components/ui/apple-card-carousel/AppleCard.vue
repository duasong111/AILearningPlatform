<script setup lang="ts">
import { onClickOutside } from "@vueuse/core";
import { AnimatePresence, Motion } from "motion-v";
import { inject, onMounted, onUnmounted, ref, watch } from "vue";
import { CarouselKey } from "./AppleCarouselContext";

interface Card {
  src: string;
  title: string;
  category: string;
}

interface Props {
  card: Card;
  index: number;
  layout?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  layout: false,
});

const open = ref(false);
const containerRef = ref<HTMLDivElement | null>(null);
const carouselContext = inject(CarouselKey);

if (!carouselContext) {
  throw new Error("Card must be used within a Carousel");
}

const { onCardClose, currentIndex } = carouselContext;

function handleKeyDown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    handleClose();
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyDown);
});

watch(open, (newVal) => {
  if (newVal) {
    document.body.style.overflow = "hidden";
  } else {
    document.body.style.overflow = "auto";
  }
});

onClickOutside(containerRef, () => handleClose());

function handleOpen() {
  open.value = true;
}

function handleClose() {
  open.value = false;
  onCardClose(props.index);
}
</script>

<template>
  <Teleport to="body">
    <AnimatePresence>
      <div
        v-if="open"
        class="fixed inset-0 z-50 h-screen overflow-auto flex items-center justify-center p-6"
      >
        <Motion
          as="div"
          :initial="{ opacity: 0 }"
          :animate="{ opacity: 1 }"
          :exit="{ opacity: 0 }"
          class="fixed inset-0 size-full bg-black/80 backdrop-blur-lg"
        />
        <Motion
          ref="containerRef"
          as="div"
          :initial="{ opacity: 0 }"
          :animate="{ opacity: 1 }"
          :exit="{ opacity: 0 }"
          :layout-id="layout ? `card-${card.title}` : undefined"
          class="relative z-60 w-full max-w-xl h-fit rounded-3xl bg-white p-4 font-sans md:p-8 dark:bg-neutral-900"
        >
          <button
            class="sticky top-4 right-0 ml-auto flex size-8 items-center justify-center rounded-full bg-black dark:bg-white"
            @click="handleClose"
          >
            <Icon
              name="tabler:x"
              class="size-6 text-neutral-100 dark:text-neutral-900"
            />
          </button>
          <Motion
            as="div"
            :layout-id="layout ? `category-${card.title}` : undefined"
            class="text-base font-medium text-black dark:text-white text-center w-full"
          >
            {{ card.category }}
          </Motion>
          <Motion
            as="div"
            :layout-id="layout ? `title-${card.title}` : undefined"
            class="mt-4 text-2xl font-semibold text-neutral-700 md:text-4xl dark:text-white text-center"
          >
            {{ card.title }}
          </Motion>
          <div class="py-8 text-center">
            <slot />
          </div>
        </Motion>
      </div>
    </AnimatePresence>
  </Teleport>

  <Motion
    :layout-id="layout ? `card-${card.title}` : undefined"
    class="relative z-10 flex h-56 w-40 flex-col items-start justify-start overflow-hidden rounded-3xl bg-gray-100 md:h-96 md:w-64 dark:bg-neutral-900"
    @click="handleOpen"
  >
    <div
      class="pointer-events-none absolute inset-x-0 top-0 z-30 h-full bg-linear-to-b from-black/50 via-transparent to-transparent"
    />
    <div class="relative z-40 p-8 flex flex-col items-center justify-center w-full h-full text-center">
      <Motion
        :layout-id="layout ? `category-${card.category}` : undefined"
        class="font-sans text-sm font-medium text-white md:text-base"
      >
        {{ card.category }}
      </Motion>
      <Motion
        :layout-id="layout ? `title-${card.title}` : undefined"
        class="mt-2 max-w-xs font-sans text-xl font-semibold text-balance text-white md:text-3xl"
      >
        {{ card.title }}
      </Motion>
    </div>
    <AppleBlurImage
      :src="card.src"
      :alt="card.title"
      class="absolute inset-0 z-10 object-cover"
      :fill="true"
    />
  </Motion>
</template>
