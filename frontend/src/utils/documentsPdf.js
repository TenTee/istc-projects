/**
 * Téléchargement des documents PDF générés par l'API (reçus, factures).
 * Les routes exigent le jeton de connexion : on passe par apiClient (axios) puis par un
 * lien temporaire, au lieu d'un simple <a href> qui n'enverrait pas le jeton.
 */
import { apiClient, getApiErrorMessage } from '../services/api/client';

function nomDepuisEntete(entete, defaut) {
  const trouve = /filename="?([^";]+)"?/i.exec(entete || '');
  return trouve ? trouve[1] : defaut;
}

async function messageErreur(error, defaut) {
  // Avec responseType 'blob', le message d'erreur JSON du serveur arrive sous forme de Blob.
  const data = error?.response?.data;
  if (data instanceof Blob) {
    try {
      const texte = await data.text();
      return getApiErrorMessage({ response: { data: JSON.parse(texte) } }, defaut);
    } catch {
      return defaut;
    }
  }
  if (error?.response?.status === 403) return "Vous n'avez pas accès à ce document.";
  return getApiErrorMessage(error, defaut);
}

/**
 * mode 'telecharger' : enregistre le fichier ; mode 'ouvrir' : l'ouvre dans un nouvel onglet
 * (pour l'imprimer). Renvoie true si tout s'est bien passé, sinon lève une Error lisible.
 */
export async function obtenirPdf(url, { mode = 'telecharger', nomParDefaut = 'document.pdf' } = {}) {
  // L'onglet est ouvert tout de suite (dans le clic), sinon le navigateur le bloquerait.
  const onglet = mode === 'ouvrir' ? window.open('', '_blank') : null;
  try {
    const reponse = await apiClient.get(url, {
      responseType: 'blob',
      params: { telecharger: mode === 'ouvrir' ? 0 : 1 },
    });
    const blob = new Blob([reponse.data], { type: 'application/pdf' });
    const lien = URL.createObjectURL(blob);
    if (onglet) {
      onglet.location.href = lien;
    } else {
      const a = document.createElement('a');
      a.href = lien;
      a.download = nomDepuisEntete(reponse.headers?.['content-disposition'], nomParDefaut);
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
    window.setTimeout(() => URL.revokeObjectURL(lien), 60000);
    return true;
  } catch (error) {
    if (onglet) onglet.close();
    throw new Error(await messageErreur(error, 'Le document PDF n’a pas pu être généré.'));
  }
}
