// @ts-check

import eslint from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'

export default tseslint.config(
  // Global ignores
  {
    ignores: [
      'dist/',
      'node_modules/',
      '*.config.*',
      'e2e/',
      '.husky/',
    ],
  },

  // Base JS/TS rules
  eslint.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  ...pluginVue.configs['flat/recommended'],

  // Vue parser override
  {
    files: ['src/**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        project: './tsconfig.app.json',
        extraFileExtensions: ['.vue'],
      },
    },
  },

  // TypeScript source files
  {
    files: ['src/**/*.ts', 'src/**/*.tsx'],
    languageOptions: {
      parserOptions: {
        project: './tsconfig.app.json',
      },
    },
  },

  // Browser environment (for document, window globals)
  {
    files: ['src/**/*.{ts,vue}'],
    languageOptions: {
      globals: {
        document: 'readonly',
        window: 'readonly',
        console: 'readonly',
        localStorage: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        fetch: 'readonly',
        URL: 'readonly',
        Blob: 'readonly',
        FileReader: 'readonly',
        location: 'readonly',
        navigator: 'readonly',
      },
    },
  },

  // Custom rules
  {
    rules: {
      // Allow unused vars with underscore prefix
      '@typescript-eslint/no-unused-vars': ['error', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
      }],

      // Disable type-safety rules (too many warnings, need gradual migration)
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unsafe-assignment': 'warn',
      '@typescript-eslint/no-unsafe-member-access': 'warn',
      '@typescript-eslint/no-unsafe-call': 'warn',
      '@typescript-eslint/no-unsafe-return': 'warn',
      '@typescript-eslint/no-unsafe-argument': 'warn',
      '@typescript-eslint/restrict-template-expressions': 'off',

      // no-undef handled by TypeScript
      'no-undef': 'off',

      // 组件内对 any 类型 prop 的直接修改（v-model 模式下的表单组件）
      'vue/no-mutating-props': 'off',

      // Axios interceptor 中传播 AxiosError 是标准模式
      '@typescript-eslint/prefer-promise-reject-errors': 'off',

      // Allow floating promises with void operator
      '@typescript-eslint/no-floating-promises': ['error', {
        ignoreVoid: true,
      }],

      // Require explicit return types on exported functions
      '@typescript-eslint/explicit-function-return-type': 'off',

      // Vue: allow multi-word component names in specific patterns
      'vue/multi-word-component-names': 'off',

      // Vue: require `v-bind:key` in `v-for`
      'vue/require-v-for-key': 'error',

      // Vue: no side-effects in computed properties
      'vue/no-side-effects-in-computed-properties': 'error',

      // Vue: disable verbose formatting rules (prettier handles this)
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/html-indent': 'off',
      'vue/html-closing-bracket-spacing': 'off',
      'vue/first-attribute-linebreak': 'off',
      'vue/no-multi-spaces': 'off',
      'vue/attributes-order': 'off',
      'vue/multiline-html-element-content-newline': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/mustache-interpolation-spacing': 'off',
      'vue/html-quotes': 'off',

      // Return statements in callbacks of array methods
      'array-callback-return': 'error',

      // No console.log in production
      'no-console': ['error', { allow: ['warn', 'error'] }],
    },
  },
)
