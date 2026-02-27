import confetti from "canvas-confetti";

// simple helper: fire confetti burst
export function fireConfetti() {
  confetti({
    particleCount: 150,
    spread: 60,
    origin: { y: 0.6 },
  });
}
