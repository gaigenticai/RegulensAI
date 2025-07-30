/**
 * Training Portal API Service
 * Handles all API calls related to the training portal functionality
 */

import { apiClient } from './apiClient';

class TrainingAPIService {
  constructor() {
    this.baseURL = '/api/v1/training';
  }

  // ============================================================================
  // TRAINING MODULES
  // ============================================================================

  /**
   * Get all available training modules with pagination
   */
  async getModules(filters = {}, page = 1, size = 20) {
    try {
      const params = new URLSearchParams();

      // Pagination
      params.append('page', page);
      params.append('size', size);

      // Filters
      if (filters.category && filters.category !== 'all') {
        params.append('category', filters.category);
      }
      if (filters.difficulty_level && filters.difficulty_level !== 'all') {
        params.append('difficulty_level', filters.difficulty_level);
      }
      if (filters.search) {
        params.append('search', filters.search);
      }

      const response = await apiClient.get(`${this.baseURL}/modules?${params}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch training modules:', error);
      throw error;
    }
  }

  /**
   * Get a specific training module by ID
   */
  async getModule(moduleId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/modules/${moduleId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch module ${moduleId}:`, error);
      throw error;
    }
  }

  /**
   * Get sections for a training module
   */
  async getModuleSections(moduleId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/modules/${moduleId}/sections`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch sections for module ${moduleId}:`, error);
      throw error;
    }
  }

  /**
   * Get a specific section
   */
  async getSection(sectionId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/sections/${sectionId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch section ${sectionId}:`, error);
      throw error;
    }
  }

  /**
   * Search training modules using new search endpoint
   */
  async searchModules(query, filters = {}, limit = 20) {
    try {
      const searchRequest = {
        query: query,
        category: filters.category !== 'all' ? filters.category : null,
        difficulty_level: filters.difficulty_level !== 'all' ? filters.difficulty_level : null,
        content_type: filters.content_type !== 'all' ? filters.content_type : null,
        limit: limit
      };

      const response = await apiClient.post(`${this.baseURL}/search`, searchRequest);
      return response.data;
    } catch (error) {
      console.error('Failed to search training modules:', error);
      throw error;
    }
  }

  /**
   * Get training recommendations for current user
   */
  async getRecommendations(limit = 10) {
    try {
      const response = await apiClient.get(`${this.baseURL}/recommendations?limit=${limit}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get training recommendations:', error);
      throw error;
    }
  }

  // ============================================================================
  // ENROLLMENTS AND PROGRESS
  // ============================================================================

  /**
   * Get current user's enrollments
   */
  async getUserEnrollments(status = null) {
    try {
      const params = new URLSearchParams();
      if (status) {
        params.append('status', status);
      }
      const response = await apiClient.get(`${this.baseURL}/enrollments?${params}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch user enrollments:', error);
      throw error;
    }
  }

  /**
   * Enroll user in a module
   */
  async enrollInModule(moduleId, targetCompletionDate = null, notes = null) {
    try {
      const enrollmentData = {
        module_id: moduleId,
        target_completion_date: targetCompletionDate,
        notes: notes
      };
      const response = await apiClient.post(`${this.baseURL}/enrollments`, enrollmentData);
      return response.data;
    } catch (error) {
      console.error(`Failed to enroll in module ${moduleId}:`, error);
      throw error;
    }
  }

  /**
   * Update enrollment progress
   */
  async updateEnrollmentProgress(enrollmentId, progressData) {
    try {
      const response = await apiClient.patch(`${this.baseURL}/enrollments/${enrollmentId}`, progressData);
      return response.data;
    } catch (error) {
      console.error(`Failed to update enrollment ${enrollmentId}:`, error);
      throw error;
    }
  }

  /**
   * Get section progress for an enrollment
   */
  async getSectionProgress(enrollmentId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/enrollments/${enrollmentId}/progress`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch section progress for enrollment ${enrollmentId}:`, error);
      throw error;
    }
  }

  /**
   * Update section progress
   */
  async updateSectionProgress(enrollmentId, sectionId, progressData) {
    try {
      const response = await apiClient.post(`${this.baseURL}/enrollments/${enrollmentId}/sections/${sectionId}/progress`, progressData);
      return response.data;
    } catch (error) {
      console.error(`Failed to update section progress:`, error);
      throw error;
    }
  }

  /**
   * Mark section as completed
   */
  async completeSectionProgress(enrollmentId, sectionId, timeSpent = 0, notes = '') {
    try {
      const response = await apiClient.post(`${this.baseURL}/enrollments/${enrollmentId}/sections/${sectionId}/complete`, {
        time_spent_minutes: timeSpent,
        notes: notes
      });
      return response.data;
    } catch (error) {
      console.error(`Failed to complete section:`, error);
      throw error;
    }
  }

  // ============================================================================
  // ASSESSMENTS
  // ============================================================================

  /**
   * Get assessments for a module
   */
  async getModuleAssessments(moduleId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/modules/${moduleId}/assessments`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch assessments for module ${moduleId}:`, error);
      throw error;
    }
  }

  /**
   * Start an assessment attempt
   */
  async startAssessmentAttempt(assessmentId, enrollmentId) {
    try {
      const response = await apiClient.post(`${this.baseURL}/assessments/${assessmentId}/attempts`, {
        enrollment_id: enrollmentId
      });
      return response.data;
    } catch (error) {
      console.error(`Failed to start assessment attempt:`, error);
      throw error;
    }
  }

  /**
   * Submit assessment answers
   */
  async submitAssessment(assessmentId, answers, timeSpentMinutes = null) {
    try {
      const submission = {
        assessment_id: assessmentId,
        answers: answers,
        time_spent_minutes: timeSpentMinutes
      };
      const response = await apiClient.post(`${this.baseURL}/assessments/${assessmentId}/submit`, submission);
      return response.data;
    } catch (error) {
      console.error(`Failed to submit assessment:`, error);
      throw error;
    }
  }

  /**
   * Get assessment attempt results
   */
  async getAssessmentResults(attemptId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/assessment-attempts/${attemptId}/results`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch assessment results:`, error);
      throw error;
    }
  }

  /**
   * Get user's assessment attempts
   */
  async getUserAssessmentAttempts(userId, assessmentId = null) {
    try {
      const params = new URLSearchParams();
      params.append('user_id', userId);
      if (assessmentId) {
        params.append('assessment_id', assessmentId);
      }

      const response = await apiClient.get(`${this.baseURL}/assessment-attempts?${params}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch assessment attempts:', error);
      throw error;
    }
  }

  // ============================================================================
  // BOOKMARKS
  // ============================================================================

  /**
   * Get user bookmarks
   */
  async getUserBookmarks(userId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/bookmarks?user_id=${userId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch user bookmarks:', error);
      throw error;
    }
  }

  /**
   * Create a bookmark
   */
  async createBookmark(bookmarkData) {
    try {
      const response = await apiClient.post(`${this.baseURL}/bookmarks`, bookmarkData);
      return response.data;
    } catch (error) {
      console.error('Failed to create bookmark:', error);
      throw error;
    }
  }

  /**
   * Remove a bookmark
   */
  async removeBookmark(bookmarkId) {
    try {
      const response = await apiClient.delete(`${this.baseURL}/bookmarks/${bookmarkId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to remove bookmark ${bookmarkId}:`, error);
      throw error;
    }
  }

  /**
   * Update bookmark
   */
  async updateBookmark(bookmarkId, updateData) {
    try {
      const response = await apiClient.patch(`${this.baseURL}/bookmarks/${bookmarkId}`, updateData);
      return response.data;
    } catch (error) {
      console.error(`Failed to update bookmark ${bookmarkId}:`, error);
      throw error;
    }
  }

  // ============================================================================
  // CERTIFICATES
  // ============================================================================

  /**
   * Get user certificates
   */
  async getUserCertificates(userId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/certificates?user_id=${userId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch user certificates:', error);
      throw error;
    }
  }

  /**
   * Generate certificate for completed module
   */
  async generateCertificate(enrollmentId) {
    try {
      const response = await apiClient.post(`${this.baseURL}/certificates/generate`, {
        enrollment_id: enrollmentId
      });
      return response.data;
    } catch (error) {
      console.error('Failed to generate certificate:', error);
      throw error;
    }
  }

  /**
   * Download certificate
   */
  async downloadCertificate(certificateId, format = 'pdf') {
    try {
      const response = await apiClient.get(`${this.baseURL}/certificates/${certificateId}/download?format=${format}`, {
        responseType: 'blob'
      });
      return response.data;
    } catch (error) {
      console.error(`Failed to download certificate ${certificateId}:`, error);
      throw error;
    }
  }

  /**
   * Verify certificate
   */
  async verifyCertificate(verificationCode) {
    try {
      const response = await apiClient.get(`${this.baseURL}/certificates/verify/${verificationCode}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to verify certificate:`, error);
      throw error;
    }
  }

  // ============================================================================
  // DISCUSSIONS
  // ============================================================================

  /**
   * Get discussions for a module
   */
  async getModuleDiscussions(moduleId, sectionId = null) {
    try {
      const params = new URLSearchParams();
      if (sectionId) {
        params.append('section_id', sectionId);
      }

      const response = await apiClient.get(`${this.baseURL}/modules/${moduleId}/discussions?${params}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch discussions for module ${moduleId}:`, error);
      throw error;
    }
  }

  /**
   * Create a discussion post
   */
  async createDiscussionPost(postData) {
    try {
      const response = await apiClient.post(`${this.baseURL}/discussions`, postData);
      return response.data;
    } catch (error) {
      console.error('Failed to create discussion post:', error);
      throw error;
    }
  }

  /**
   * Reply to a discussion
   */
  async replyToDiscussion(parentId, replyData) {
    try {
      const response = await apiClient.post(`${this.baseURL}/discussions/${parentId}/replies`, replyData);
      return response.data;
    } catch (error) {
      console.error(`Failed to reply to discussion ${parentId}:`, error);
      throw error;
    }
  }

  /**
   * Vote on a discussion
   */
  async voteOnDiscussion(discussionId, voteType) {
    try {
      const response = await apiClient.post(`${this.baseURL}/discussions/${discussionId}/vote`, {
        vote_type: voteType
      });
      return response.data;
    } catch (error) {
      console.error(`Failed to vote on discussion ${discussionId}:`, error);
      throw error;
    }
  }

  // ============================================================================
  // ANALYTICS AND REPORTING
  // ============================================================================

  /**
   * Track analytics event
   */
  async trackEvent(eventData) {
    try {
      const response = await apiClient.post(`${this.baseURL}/analytics/events`, eventData);
      return response.data;
    } catch (error) {
      console.error('Failed to track analytics event:', error);
      // Don't throw error for analytics to avoid disrupting user experience
    }
  }

  /**
   * Get user analytics
   */
  async getUserAnalytics(userId, dateRange = null) {
    try {
      const params = new URLSearchParams();
      params.append('user_id', userId);
      if (dateRange) {
        params.append('start_date', dateRange.start);
        params.append('end_date', dateRange.end);
      }

      const response = await apiClient.get(`${this.baseURL}/analytics/user?${params}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch user analytics:', error);
      throw error;
    }
  }

  /**
   * Generate training report
   */
  async generateReport(reportType, parameters) {
    try {
      const response = await apiClient.post(`${this.baseURL}/reports/generate`, {
        report_type: reportType,
        parameters: parameters
      });
      return response.data;
    } catch (error) {
      console.error('Failed to generate training report:', error);
      throw error;
    }
  }

  /**
   * Get available reports
   */
  async getReports(userId = null) {
    try {
      const params = new URLSearchParams();
      if (userId) {
        params.append('user_id', userId);
      }

      const response = await apiClient.get(`${this.baseURL}/reports?${params}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch reports:', error);
      throw error;
    }
  }

  // ============================================================================
  // ACHIEVEMENTS
  // ============================================================================

  /**
   * Get user achievements
   */
  async getUserAchievements(userId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/achievements?user_id=${userId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch user achievements:', error);
      throw error;
    }
  }

  /**
   * Check for new achievements
   */
  async checkAchievements(userId) {
    try {
      const response = await apiClient.post(`${this.baseURL}/achievements/check`, {
        user_id: userId
      });
      return response.data;
    } catch (error) {
      console.error('Failed to check achievements:', error);
      throw error;
    }
  }

  // ============================================================================
  // ENHANCED ANALYTICS
  // ============================================================================

  /**
   * Get training dashboard analytics
   */
  async getDashboardAnalytics() {
    try {
      const response = await apiClient.get(`${this.baseURL}/analytics/dashboard`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch dashboard analytics:', error);
      throw error;
    }
  }

  /**
   * Get user analytics
   */
  async getUserAnalytics(userId = null) {
    try {
      const endpoint = userId ?
        `${this.baseURL}/analytics/user/${userId}` :
        `${this.baseURL}/analytics/user/me`;
      const response = await apiClient.get(endpoint);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch user analytics:', error);
      throw error;
    }
  }

  /**
   * Track analytics event
   */
  async trackEvent(eventType, eventData = {}, moduleId = null, sectionId = null, sessionId = null) {
    try {
      const trackingData = {
        event_type: eventType,
        data: eventData,
        module_id: moduleId,
        section_id: sectionId,
        session_id: sessionId || this.generateSessionId()
      };
      const response = await apiClient.post(`${this.baseURL}/analytics/track`, trackingData);
      return response.data;
    } catch (error) {
      console.error('Failed to track analytics event:', error);
      // Don't throw error for analytics tracking failures
      return { success: false };
    }
  }

  /**
   * Generate a session ID for analytics tracking
   */
  generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // ============================================================================
  // ENHANCED CERTIFICATES
  // ============================================================================

  /**
   * Download a certificate with proper file handling
   */
  async downloadCertificate(certificateId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/certificates/${certificateId}/download`);
      return response.data;
    } catch (error) {
      console.error(`Failed to download certificate ${certificateId}:`, error);
      throw error;
    }
  }

  /**
   * Verify a certificate
   */
  async verifyCertificate(verificationCode) {
    try {
      const response = await apiClient.get(`${this.baseURL}/certificates/verify/${verificationCode}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to verify certificate ${verificationCode}:`, error);
      throw error;
    }
  }
}

// Export singleton instance
export const TrainingAPI = new TrainingAPIService();
