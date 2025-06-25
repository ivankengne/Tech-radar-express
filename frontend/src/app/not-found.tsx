export default function NotFound() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
          404 - Page non trouvée
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          La page que vous cherchez n&apos;existe pas.
        </p>
        <a 
          href="/" 
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
        >
          Retour à l&apos;accueil
        </a>
      </div>
    </div>
  );
} 