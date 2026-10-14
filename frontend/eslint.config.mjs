import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = defineConfig([
  ...nextVitals,
  {
    rules: {
      // Textes de l'interface en français : les apostrophes dans le JSX sont voulues
      // et correctement affichées par React.
      "react/no-unescaped-entities": "off",
      // Règle récente du React Compiler : signalée en avertissement le temps de
      // migrer les composants concernés (voir docs/developpeurs/conventions.md).
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
