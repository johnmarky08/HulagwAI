export function initScrollReveal(root) {
    if (!root || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return () => {};

    const elements = [...root.querySelectorAll(".scroll-reveal")];
    if (!elements.length) return () => {};
    elements.forEach((element) => element.classList.add("reveal-pending"));

    if (!("IntersectionObserver" in window)) {
        elements.forEach((element) => element.classList.add("is-visible"));
        return () => {};
    }

    const observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
            if (!entry.isIntersecting) continue;
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
        }
    }, { threshold: 0.12, rootMargin: "0px 0px -4% 0px" });

    for (const element of elements) observer.observe(element);
    return () => observer.disconnect();
}
