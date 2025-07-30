import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Card,
  CardContent,
  Alert,
  Tabs,
  Tab,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  FormControlLabel,
  TextField,
  Radio,
  RadioGroup,
  FormControl,
  FormLabel
} from '@mui/material';
import {
  ExpandMore,
  PlayArrow,
  Pause,
  CheckCircle,
  Bookmark,
  BookmarkBorder,
  Print,
  Download,
  Share,
  Lightbulb,
  Warning,
  Info,
  Code,
  Quiz,
  Assignment,
  VideoLibrary,
  NavigateNext,
  NavigateBefore,
  Home,
  MenuBook,
  Timer,
  School
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ReactMarkdown from 'react-markdown';
import { TrainingAPI } from '../../services/TrainingAPI';

const InteractiveTrainingContent = ({
  module,
  sections,
  enrollment,
  onProgressUpdate,
  onSectionComplete,
  onBookmark
}) => {
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [sectionProgress, setSectionProgress] = useState({});
  const [timeSpent, setTimeSpent] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [bookmarks, setBookmarks] = useState([]);
  const [showQuiz, setShowQuiz] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [quizResults, setQuizResults] = useState(null);
  const [expandedSections, setExpandedSections] = useState({});
  const [completedExercises, setCompletedExercises] = useState({});
  
  const timerRef = useRef(null);
  const contentRef = useRef(null);

  const currentSection = sections[currentSectionIndex];

  useEffect(() => {
    // Load section progress
    loadSectionProgress();
    
    // Start timer when component mounts
    startTimer();
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    // Track analytics when section changes
    if (currentSection) {
      TrainingAPI.trackEvent({
        event_type: 'section_start',
        module_id: module.id,
        section_id: currentSection.id,
        timestamp: new Date().toISOString()
      });
    }
  }, [currentSectionIndex]);

  const loadSectionProgress = async () => {
    try {
      const progress = await TrainingAPI.getSectionProgress(enrollment.id);
      const progressMap = {};
      progress.forEach(p => {
        progressMap[p.section_id] = p;
      });
      setSectionProgress(progressMap);
    } catch (error) {
      console.error('Failed to load section progress:', error);
    }
  };

  const startTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    
    timerRef.current = setInterval(() => {
      setTimeSpent(prev => prev + 1);
    }, 60000); // Update every minute
  };

  const handleSectionComplete = async () => {
    try {
      await TrainingAPI.completeSectionProgress(
        enrollment.id,
        currentSection.id,
        timeSpent,
        'Section completed'
      );
      
      // Update local progress
      setSectionProgress(prev => ({
        ...prev,
        [currentSection.id]: {
          ...prev[currentSection.id],
          status: 'completed',
          completed_at: new Date().toISOString()
        }
      }));

      // Track completion event
      TrainingAPI.trackEvent({
        event_type: 'section_complete',
        module_id: module.id,
        section_id: currentSection.id,
        time_spent_minutes: timeSpent
      });

      if (onSectionComplete) {
        onSectionComplete(currentSection.id);
      }

      // Auto-advance to next section
      if (currentSectionIndex < sections.length - 1) {
        setTimeout(() => {
          setCurrentSectionIndex(prev => prev + 1);
        }, 1000);
      }
    } catch (error) {
      console.error('Failed to complete section:', error);
    }
  };

  const handleBookmarkSection = async () => {
    try {
      await TrainingAPI.createBookmark({
        module_id: module.id,
        section_id: currentSection.id,
        title: `${module.title} - ${currentSection.title}`,
        description: 'Bookmarked during training'
      });
      
      setBookmarks(prev => [...prev, currentSection.id]);
      
      if (onBookmark) {
        onBookmark(module.id, currentSection.id);
      }
    } catch (error) {
      console.error('Failed to bookmark section:', error);
    }
  };

  const renderCodeBlock = ({ language, value }) => (
    <Box sx={{ my: 2 }}>
      <SyntaxHighlighter
        language={language || 'text'}
        style={tomorrow}
        customStyle={{
          borderRadius: '8px',
          fontSize: '14px'
        }}
      >
        {value}
      </SyntaxHighlighter>
    </Box>
  );

  const renderInteractiveExercise = (exercise) => {
    const isCompleted = completedExercises[exercise.id];
    
    return (
      <Card sx={{ my: 2, border: '2px solid', borderColor: isCompleted ? 'success.main' : 'primary.main' }}>
        <CardContent>
          <Box display="flex" alignItems="center" mb={2}>
            <Assignment color={isCompleted ? 'success' : 'primary'} sx={{ mr: 1 }} />
            <Typography variant="h6">
              {exercise.title}
            </Typography>
            {isCompleted && <CheckCircle color="success" sx={{ ml: 'auto' }} />}
          </Box>
          
          <Typography variant="body2" paragraph>
            {exercise.description}
          </Typography>
          
          {exercise.type === 'code' && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Try this code:
              </Typography>
              {renderCodeBlock({ language: exercise.language, value: exercise.code })}
              
              <Button
                variant="outlined"
                onClick={() => setCompletedExercises(prev => ({ ...prev, [exercise.id]: true }))}
                disabled={isCompleted}
              >
                {isCompleted ? 'Completed' : 'Mark as Tried'}
              </Button>
            </Box>
          )}
          
          {exercise.type === 'checklist' && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Complete these steps:
              </Typography>
              <List>
                {exercise.steps.map((step, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      <Checkbox />
                    </ListItemIcon>
                    <ListItemText primary={step} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderQuizQuestion = (question, index) => {
    const answer = quizAnswers[question.id];
    
    return (
      <Card key={question.id} sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Question {index + 1}: {question.question}
          </Typography>
          
          {question.type === 'multiple_choice' && (
            <FormControl component="fieldset">
              <RadioGroup
                value={answer || ''}
                onChange={(e) => setQuizAnswers(prev => ({ ...prev, [question.id]: e.target.value }))}
              >
                {question.options.map((option, optIndex) => (
                  <FormControlLabel
                    key={optIndex}
                    value={option.id}
                    control={<Radio />}
                    label={option.text}
                  />
                ))}
              </RadioGroup>
            </FormControl>
          )}
          
          {question.type === 'text' && (
            <TextField
              fullWidth
              multiline
              rows={3}
              value={answer || ''}
              onChange={(e) => setQuizAnswers(prev => ({ ...prev, [question.id]: e.target.value }))}
              placeholder="Enter your answer..."
            />
          )}
          
          {question.type === 'checkbox' && (
            <Box>
              {question.options.map((option, optIndex) => (
                <FormControlLabel
                  key={optIndex}
                  control={
                    <Checkbox
                      checked={(answer || []).includes(option.id)}
                      onChange={(e) => {
                        const currentAnswers = answer || [];
                        const newAnswers = e.target.checked
                          ? [...currentAnswers, option.id]
                          : currentAnswers.filter(id => id !== option.id);
                        setQuizAnswers(prev => ({ ...prev, [question.id]: newAnswers }));
                      }}
                    />
                  }
                  label={option.text}
                />
              ))}
            </Box>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderSectionContent = (section) => {
    // Parse interactive elements from section content
    const interactiveElements = section.interactive_elements || {};
    
    return (
      <Box>
        {/* Section Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box>
            <Typography variant="h4" gutterBottom>
              {section.title}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Estimated time: {section.estimated_duration_minutes} minutes
            </Typography>
          </Box>
          
          <Box display="flex" gap={1}>
            <Tooltip title="Bookmark this section">
              <IconButton onClick={handleBookmarkSection}>
                {bookmarks.includes(section.id) ? <Bookmark color="primary" /> : <BookmarkBorder />}
              </IconButton>
            </Tooltip>
            
            <Tooltip title="Print section">
              <IconButton onClick={() => window.print()}>
                <Print />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Progress indicator */}
        <Box mb={3}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="body2">
              Section {currentSectionIndex + 1} of {sections.length}
            </Typography>
            <Typography variant="body2">
              Time spent: {timeSpent} minutes
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={(currentSectionIndex + 1) / sections.length * 100}
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>

        {/* Main Content */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <ReactMarkdown
            components={{
              code: ({ node, inline, className, children, ...props }) => {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  renderCodeBlock({ language: match[1], value: String(children).replace(/\n$/, '') })
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
              h1: ({ children }) => <Typography variant="h4" gutterBottom>{children}</Typography>,
              h2: ({ children }) => <Typography variant="h5" gutterBottom sx={{ mt: 3 }}>{children}</Typography>,
              h3: ({ children }) => <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>{children}</Typography>,
              p: ({ children }) => <Typography variant="body1" paragraph>{children}</Typography>,
              ul: ({ children }) => <List>{children}</List>,
              li: ({ children }) => (
                <ListItem>
                  <ListItemIcon>
                    <CheckCircle fontSize="small" color="primary" />
                  </ListItemIcon>
                  <ListItemText primary={children} />
                </ListItem>
              )
            }}
          >
            {section.content_markdown}
          </ReactMarkdown>
        </Paper>

        {/* Interactive Elements */}
        {interactiveElements.exercises && (
          <Box mb={3}>
            <Typography variant="h5" gutterBottom>
              <Assignment sx={{ mr: 1, verticalAlign: 'middle' }} />
              Hands-on Exercises
            </Typography>
            {interactiveElements.exercises.map(exercise => renderInteractiveExercise(exercise))}
          </Box>
        )}

        {/* Key Points */}
        {interactiveElements.keyPoints && (
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              <Lightbulb sx={{ mr: 1, verticalAlign: 'middle' }} />
              Key Points to Remember
            </Typography>
            <List>
              {interactiveElements.keyPoints.map((point, index) => (
                <ListItem key={index}>
                  <ListItemText primary={point} />
                </ListItem>
              ))}
            </List>
          </Alert>
        )}

        {/* Best Practices */}
        {interactiveElements.bestPractices && (
          <Alert severity="success" sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              <CheckCircle sx={{ mr: 1, verticalAlign: 'middle' }} />
              Best Practices
            </Typography>
            <List>
              {interactiveElements.bestPractices.map((practice, index) => (
                <ListItem key={index}>
                  <ListItemText primary={practice} />
                </ListItem>
              ))}
            </List>
          </Alert>
        )}

        {/* Common Pitfalls */}
        {interactiveElements.commonPitfalls && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              <Warning sx={{ mr: 1, verticalAlign: 'middle' }} />
              Common Pitfalls to Avoid
            </Typography>
            <List>
              {interactiveElements.commonPitfalls.map((pitfall, index) => (
                <ListItem key={index}>
                  <ListItemText primary={pitfall} />
                </ListItem>
              ))}
            </List>
          </Alert>
        )}

        {/* Section Navigation */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mt={4}>
          <Button
            startIcon={<NavigateBefore />}
            onClick={() => setCurrentSectionIndex(prev => Math.max(0, prev - 1))}
            disabled={currentSectionIndex === 0}
          >
            Previous Section
          </Button>

          <Box display="flex" gap={2}>
            {sectionProgress[section.id]?.status !== 'completed' && (
              <Button
                variant="contained"
                startIcon={<CheckCircle />}
                onClick={handleSectionComplete}
              >
                Mark as Complete
              </Button>
            )}

            {interactiveElements.quiz && (
              <Button
                variant="outlined"
                startIcon={<Quiz />}
                onClick={() => setShowQuiz(true)}
              >
                Take Quiz
              </Button>
            )}
          </Box>

          <Button
            endIcon={<NavigateNext />}
            onClick={() => setCurrentSectionIndex(prev => Math.min(sections.length - 1, prev + 1))}
            disabled={currentSectionIndex === sections.length - 1}
          >
            Next Section
          </Button>
        </Box>
      </Box>
    );
  };

  if (!currentSection) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading training content...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: '100%', mx: 'auto', p: 3 }}>
      {/* Section Stepper */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Stepper activeStep={currentSectionIndex} orientation="horizontal">
          {sections.map((section, index) => {
            const isCompleted = sectionProgress[section.id]?.status === 'completed';
            return (
              <Step key={section.id} completed={isCompleted}>
                <StepLabel
                  onClick={() => setCurrentSectionIndex(index)}
                  sx={{ cursor: 'pointer' }}
                >
                  {section.title}
                </StepLabel>
              </Step>
            );
          })}
        </Stepper>
      </Paper>

      {/* Main Content */}
      <div ref={contentRef}>
        {renderSectionContent(currentSection)}
      </div>

      {/* Quiz Dialog */}
      <Dialog
        open={showQuiz}
        onClose={() => setShowQuiz(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Quiz sx={{ mr: 1, verticalAlign: 'middle' }} />
          Section Quiz: {currentSection.title}
        </DialogTitle>
        <DialogContent>
          {currentSection.interactive_elements?.quiz?.questions?.map((question, index) =>
            renderQuizQuestion(question, index)
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowQuiz(false)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => {
              // Submit quiz logic here
              setShowQuiz(false);
            }}
          >
            Submit Quiz
          </Button>
        </DialogActions>
      </Dialog>

      {/* Floating Timer */}
      <Fab
        color="primary"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={() => setIsPlaying(!isPlaying)}
      >
        <Timer />
      </Fab>
    </Box>
  );
};

export default InteractiveTrainingContent;
