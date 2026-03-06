"use client";

import { motion, Transition } from "framer-motion";
import { ReactNode } from "react";
import { ArtDirectionTokens } from "@/types/schema";

interface MotionWrapperProps {
  children: ReactNode;
  animationFeeling: ArtDirectionTokens["animation_feeling"];
  delay?: number;
  className?: string;
}

/**
 * MotionWrapper — HOC pour gérer les animations selon animation_feeling.
 * 
 * Responsabilités :
 * - Wrapper les composants avec Framer Motion
 * - Appliquer les bonnes courbes de transition selon le feeling
 * - Gérer les animations d'apparition (fade + slide)
 * 
 * Exemples d'usage :
 * <MotionWrapper animationFeeling="snappy_springs">
 *   <h1>Titre animé</h1>
 * </MotionWrapper>
 */
export default function MotionWrapper({
  children,
  animationFeeling,
  delay = 0,
  className = "",
}: MotionWrapperProps) {
  // =========================================================================
  // Configuration des transitions selon animation_feeling
  // =========================================================================
  const transitionMap: Record<
    ArtDirectionTokens["animation_feeling"],
    Transition
  > = {
    snappy_springs: {
      type: "spring",
      stiffness: 300,
      damping: 20,
      delay,
    },
    smooth_ease: {
      type: "tween",
      duration: 0.6,
      ease: [0.4, 0, 0.2, 1], // cubic-bezier(0.4, 0, 0.2, 1)
      delay,
    },
    none: {
      duration: 0,
      delay: 0,
    },
  };

  // =========================================================================
  // Variantes d'animation (fade + slide from bottom)
  // =========================================================================
  const variants = {
    hidden: {
      opacity: 0,
      y: animationFeeling === "none" ? 0 : 20,
    },
    visible: {
      opacity: 1,
      y: 0,
    },
  };

  // Si animation_feeling === "none", retourner les children sans wrapper
  if (animationFeeling === "none") {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-100px" }}
      variants={variants}
      transition={transitionMap[animationFeeling]}
      className={className}
    >
      {children}
    </motion.div>
  );
}
