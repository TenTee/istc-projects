'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { anneesAcademiquesService } from '../services/api/services';
import { isSuperUserOrAdmin, normalizePermissionValue } from '../utils/permissions';

/**
 * Accès du compte aux années archivées (non actives) : 'none' | 'lecture' | 'ecriture'.
 * Administrateurs : 'ecriture'. Sinon : droit « Années archivées » du rôle. Le serveur
 * applique la même règle (academique/middleware.py) : ceci ne sert qu'à l'affichage.
 */
export function lireNiveauArchives() {
  if (typeof window === 'undefined') return 'none';
  let permissions = {};
  try {
    permissions = JSON.parse(localStorage.getItem('user_permissions') || '{}');
  } catch {
    permissions = {};
  }
  if (permissions.is_superuser || isSuperUserOrAdmin()) return 'ecriture';
  return normalizePermissionValue(permissions.acces_annees_archivees);
}

const MESSAGE_ARCHIVE_INTERDITE =
  "Cette année est archivée : votre rôle n'y a pas accès (droit « Années archivées »).";

const AcademicYearContext = createContext();

export const AcademicYearProvider = ({ children }) => {
  const [academicYears, setAcademicYears] = useState([]);
  const [selectedYear, setSelectedYear] = useState(null);
  const [loading, setLoading] = useState(true);
  const [yearError, setYearError] = useState(null);

  const fetchYears = async () => {
    try {
      const years = await anneesAcademiquesService.list();
      const list = Array.isArray(years) ? years : years?.results || [];
      setAcademicYears(list);

      const allowInactive = lireNiveauArchives() !== 'none';

      // Récupérer l'année stockée ou utiliser l'année active par défaut
      const storedYearId = localStorage.getItem('selectedAcademicYearId');
      const active = list.find(y => y.est_active) || list[0];
      if (storedYearId) {
        const found = list.find(y => String(y.id) === String(storedYearId));
        if (found && (found.est_active || allowInactive)) {
          setSelectedYear(found);
        } else {
          localStorage.removeItem('selectedAcademicYearId');
          setSelectedYear(active);
          if (found && !allowInactive) {
            setYearError(MESSAGE_ARCHIVE_INTERDITE);
          }
        }
      } else {
        setSelectedYear(active);
      }
    } catch (error) {
      console.error("Erreur chargement années académiques:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchYears();
  }, []);

  useEffect(() => {
    if (selectedYear) {
      localStorage.setItem('selectedAcademicYearId', selectedYear.id);
      localStorage.setItem('selectedAcademicYearLibelle', selectedYear.libelle);
      // Optionnel: Déclencher un événement global pour notifier les composants
      window.dispatchEvent(new Event('academicYearChanged'));
      setYearError(null);
    }
  }, [selectedYear]);

  const changeYear = (yearId) => {
    const year = academicYears.find(y => String(y.id) === String(yearId));
    if (!year) return;

    const allowInactive = lireNiveauArchives() !== 'none';

    if (!year.est_active && !allowInactive) {
      setYearError(MESSAGE_ARCHIVE_INTERDITE);
      return false;
    }

    setYearError(null);
    // L'intercepteur API lit cette valeur pour envoyer X-Academic-Year.
    // On l'enregistre avant le rendu suivant, afin que les requêtes de la
    // page courante utilisent immédiatement la nouvelle année.
    localStorage.setItem('selectedAcademicYearId', year.id);
    localStorage.setItem('selectedAcademicYearLibelle', year.libelle);
    setSelectedYear(year);
    window.dispatchEvent(new CustomEvent('academicYearChanged', { detail: { yearId: year.id } }));
    return true;
  };

  return (
    <AcademicYearContext.Provider value={{ 
      academicYears, 
      selectedYear, 
      changeYear, 
      loading,
      refreshYears: fetchYears,
      yearError,
      clearYearError: () => setYearError(null),
      // Année archivée sélectionnée avec un droit « lecture » : les modifications seront refusées.
      consultationSeule: Boolean(selectedYear && !selectedYear.est_active && lireNiveauArchives() === 'lecture'),
    }}>
      {children}
    </AcademicYearContext.Provider>
  );
};

export const useAcademicYear = () => {
  const context = useContext(AcademicYearContext);
  if (!context) {
    throw new Error('useAcademicYear must be used within an AcademicYearProvider');
  }
  return context;
};
