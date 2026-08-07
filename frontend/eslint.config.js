import js from '@eslint/js'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'

// ESLint reads your code and points out likely mistakes — an unused variable,
// a typo'd name, a React hook used the wrong way. CI runs it on every pull
// request, so run `npm run lint` before you push.
export default [
  { ignores: ['dist'] },
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { react, 'react-hooks': reactHooks },
    rules: {
      ...js.configs.recommended.rules,
      // Without these two, ESLint doesn't realise that using a component in
      // JSX counts as using it, and wrongly calls every import "unused".
      'react/jsx-uses-react': 'error',
      'react/jsx-uses-vars': 'error',
      ...reactHooks.configs.recommended.rules,
    },
  },
]
