/* eslint-env node */
module.exports = {
  root: true,
  env: {
    browser: true,
    node: true,
    es2022: true
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended'
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    requireConfigFile: false
  },
  ignorePatterns: [
    'dist/**',
    'node_modules/**',
    'electron/**',
    'src/auto-imports.d.ts',
    'src/components.d.ts',
    'coverage/**'
  ],
  globals: {
    // Vite/Electron 全局
    __dirname: 'off',
    __filename: 'off',
    Buffer: 'off',
    process: 'off',
    Blob: 'readonly',
    structuredClone: 'readonly',
    queueMicrotask: 'readonly',
    electronAPI: 'readonly'
  },
  rules: {
    // --- 关掉对纯 JS/Vue 脚手架噪音过大的规则,仅保留实际有帮助的 ---
    'vue/multi-word-component-names': 'off',
    'vue/no-v-html': 'off',
    'vue/no-mutating-props': 'warn',
    'vue/first-attribute-linebreak': 'off',
    'vue/singleline-html-element-content-newline': 'off',
    'vue/max-attributes-per-line': 'off',
    'vue/html-self-closing': 'off',
    'vue/html-closing-bracket-newline': 'off',
    'vue/html-indent': 'off',
    'vue/attributes-order': 'off',
    'vue/component-tags-order': 'off',
    'vue/block-order': 'off',
    'vue/comment-directive': 'off',

    // --- 通用 JS:仅警告潜在 bug,不强推风格 ---
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'none' }],
    'no-undef': 'warn',
    'no-console': 'off',
    'no-debugger': 'warn',
    'no-empty': ['warn', { allowEmptyCatch: true }],
    'no-constant-condition': 'warn',
    'no-prototype-builtins': 'off',
    'no-useless-catch': 'warn',
    'use-isnan': 'warn',
    'valid-typeof': 'warn',
    'no-case-declarations': 'off',
    'prefer-const': 'warn'
  }
}
