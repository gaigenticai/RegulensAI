import React, { useState, useEffect, useContext } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Avatar,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  Menu,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Tabs,
  Tab,
  Badge,
  Tooltip,
  Card,
  CardContent,
  CardActions,
  InputAdornment,
  Alert
} from '@mui/material';
import {
  Forum,
  Add,
  ThumbUp,
  ThumbDown,
  Reply,
  MoreVert,
  Search,
  FilterList,
  PushPin,
  CheckCircle,
  QuestionAnswer,
  Lightbulb,
  Announcement,
  Sort,
  Send,
  Edit,
  Delete,
  Flag,
  Star,
  StarBorder
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { AuthContext } from '../../contexts/AuthContext';
import { TrainingAPI } from '../../services/TrainingAPI';

const DiscussionForum = ({ moduleId = null, sectionId = null }) => {
  const { user } = useContext(AuthContext);
  const [discussions, setDiscussions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState(0);
  const [showNewPostDialog, setShowNewPostDialog] = useState(false);
  const [newPost, setNewPost] = useState({
    title: '',
    content: '',
    type: 'question'
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('recent');
  const [filterType, setFilterType] = useState('all');
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyContent, setReplyContent] = useState('');
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedPost, setSelectedPost] = useState(null);

  useEffect(() => {
    loadDiscussions();
  }, [moduleId, sectionId, sortBy, filterType]);

  const loadDiscussions = async () => {
    try {
      setLoading(true);
      let discussionsData;
      
      if (moduleId) {
        discussionsData = await TrainingAPI.getModuleDiscussions(moduleId, sectionId);
      } else {
        // Load all discussions if no specific module
        discussionsData = await TrainingAPI.getAllDiscussions();
      }
      
      setDiscussions(discussionsData);
    } catch (error) {
      console.error('Failed to load discussions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePost = async () => {
    try {
      const postData = {
        ...newPost,
        module_id: moduleId,
        section_id: sectionId
      };
      
      await TrainingAPI.createDiscussionPost(postData);
      
      setNewPost({ title: '', content: '', type: 'question' });
      setShowNewPostDialog(false);
      await loadDiscussions();
    } catch (error) {
      console.error('Failed to create post:', error);
    }
  };

  const handleReply = async (parentId) => {
    try {
      await TrainingAPI.replyToDiscussion(parentId, {
        content: replyContent,
        discussion_type: 'answer'
      });
      
      setReplyContent('');
      setReplyingTo(null);
      await loadDiscussions();
    } catch (error) {
      console.error('Failed to reply:', error);
    }
  };

  const handleVote = async (discussionId, voteType) => {
    try {
      await TrainingAPI.voteOnDiscussion(discussionId, voteType);
      await loadDiscussions();
    } catch (error) {
      console.error('Failed to vote:', error);
    }
  };

  const getDiscussionIcon = (type) => {
    switch (type) {
      case 'question':
        return <QuestionAnswer color="primary" />;
      case 'tip':
        return <Lightbulb color="warning" />;
      case 'announcement':
        return <Announcement color="error" />;
      default:
        return <Forum color="action" />;
    }
  };

  const getDiscussionColor = (type) => {
    switch (type) {
      case 'question':
        return 'primary';
      case 'tip':
        return 'warning';
      case 'announcement':
        return 'error';
      default:
        return 'default';
    }
  };

  const filteredDiscussions = discussions.filter(discussion => {
    const matchesSearch = discussion.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         discussion.content?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'all' || discussion.discussion_type === filterType;
    return matchesSearch && matchesType;
  });

  const sortedDiscussions = [...filteredDiscussions].sort((a, b) => {
    switch (sortBy) {
      case 'recent':
        return new Date(b.created_at) - new Date(a.created_at);
      case 'popular':
        return (b.upvotes - b.downvotes) - (a.upvotes - a.downvotes);
      case 'unanswered':
        return (a.replies?.length || 0) - (b.replies?.length || 0);
      default:
        return 0;
    }
  });

  const renderDiscussionCard = (discussion) => (
    <Card key={discussion.id} sx={{ mb: 2 }}>
      <CardContent>
        {/* Header */}
        <Box display="flex" alignItems="flex-start" mb={2}>
          <Avatar sx={{ mr: 2 }}>
            {discussion.user_name?.charAt(0) || 'U'}
          </Avatar>
          
          <Box flexGrow={1}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              {getDiscussionIcon(discussion.discussion_type)}
              <Typography variant="h6" component="h3">
                {discussion.title}
              </Typography>
              
              {discussion.is_pinned && (
                <PushPin color="primary" fontSize="small" />
              )}
              
              {discussion.is_resolved && (
                <CheckCircle color="success" fontSize="small" />
              )}
              
              <Chip
                label={discussion.discussion_type}
                color={getDiscussionColor(discussion.discussion_type)}
                size="small"
              />
            </Box>
            
            <Typography variant="body2" color="textSecondary" gutterBottom>
              by {discussion.user_name} • {formatDistanceToNow(new Date(discussion.created_at))} ago
            </Typography>
            
            <Typography variant="body1" paragraph>
              {discussion.content}
            </Typography>
            
            {/* Tags */}
            {discussion.tags && discussion.tags.length > 0 && (
              <Box display="flex" gap={1} mb={2}>
                {discussion.tags.map((tag, index) => (
                  <Chip key={index} label={tag} size="small" variant="outlined" />
                ))}
              </Box>
            )}
          </Box>
          
          <IconButton
            onClick={(e) => {
              setAnchorEl(e.currentTarget);
              setSelectedPost(discussion);
            }}
          >
            <MoreVert />
          </IconButton>
        </Box>
        
        {/* Actions */}
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={2}>
            <Box display="flex" alignItems="center">
              <IconButton
                size="small"
                onClick={() => handleVote(discussion.id, 'upvote')}
                color={discussion.user_vote === 'upvote' ? 'primary' : 'default'}
              >
                <ThumbUp fontSize="small" />
              </IconButton>
              <Typography variant="body2" sx={{ mx: 1 }}>
                {discussion.upvotes || 0}
              </Typography>
              <IconButton
                size="small"
                onClick={() => handleVote(discussion.id, 'downvote')}
                color={discussion.user_vote === 'downvote' ? 'error' : 'default'}
              >
                <ThumbDown fontSize="small" />
              </IconButton>
            </Box>
            
            <Button
              size="small"
              startIcon={<Reply />}
              onClick={() => setReplyingTo(discussion.id)}
            >
              Reply ({discussion.replies?.length || 0})
            </Button>
          </Box>
          
          <Typography variant="body2" color="textSecondary">
            {discussion.module_title && `in ${discussion.module_title}`}
          </Typography>
        </Box>
        
        {/* Reply Form */}
        {replyingTo === discussion.id && (
          <Box mt={2} p={2} bgcolor="grey.50" borderRadius={1}>
            <TextField
              fullWidth
              multiline
              rows={3}
              placeholder="Write your reply..."
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              sx={{ mb: 2 }}
            />
            <Box display="flex" gap={1}>
              <Button
                variant="contained"
                size="small"
                startIcon={<Send />}
                onClick={() => handleReply(discussion.id)}
                disabled={!replyContent.trim()}
              >
                Post Reply
              </Button>
              <Button
                size="small"
                onClick={() => {
                  setReplyingTo(null);
                  setReplyContent('');
                }}
              >
                Cancel
              </Button>
            </Box>
          </Box>
        )}
        
        {/* Replies */}
        {discussion.replies && discussion.replies.length > 0 && (
          <Box mt={2}>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="subtitle2" gutterBottom>
              Replies ({discussion.replies.length})
            </Typography>
            
            {discussion.replies.map((reply) => (
              <Box key={reply.id} display="flex" mb={2}>
                <Avatar sx={{ mr: 2, width: 32, height: 32 }}>
                  {reply.user_name?.charAt(0) || 'U'}
                </Avatar>
                <Box flexGrow={1}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <Typography variant="body2" fontWeight="bold">
                      {reply.user_name}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {formatDistanceToNow(new Date(reply.created_at))} ago
                    </Typography>
                    {reply.is_best_answer && (
                      <Chip
                        icon={<CheckCircle />}
                        label="Best Answer"
                        color="success"
                        size="small"
                      />
                    )}
                  </Box>
                  <Typography variant="body2">
                    {reply.content}
                  </Typography>
                </Box>
              </Box>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );

  const tabLabels = [
    { label: 'All Discussions', value: 'all' },
    { label: 'Questions', value: 'question' },
    { label: 'Tips & Tricks', value: 'tip' },
    { label: 'Announcements', value: 'announcement' }
  ];

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" gutterBottom>
          <Forum sx={{ mr: 1, verticalAlign: 'middle' }} />
          Discussion Forum
        </Typography>
        
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setShowNewPostDialog(true)}
        >
          New Discussion
        </Button>
      </Box>

      {/* Search and Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
          <TextField
            size="small"
            placeholder="Search discussions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              )
            }}
            sx={{ flexGrow: 1, minWidth: 200 }}
          />
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Sort By</InputLabel>
            <Select
              value={sortBy}
              label="Sort By"
              onChange={(e) => setSortBy(e.target.value)}
            >
              <MenuItem value="recent">Most Recent</MenuItem>
              <MenuItem value="popular">Most Popular</MenuItem>
              <MenuItem value="unanswered">Unanswered</MenuItem>
            </Select>
          </FormControl>
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Type</InputLabel>
            <Select
              value={filterType}
              label="Type"
              onChange={(e) => setFilterType(e.target.value)}
            >
              <MenuItem value="all">All Types</MenuItem>
              <MenuItem value="question">Questions</MenuItem>
              <MenuItem value="tip">Tips</MenuItem>
              <MenuItem value="announcement">Announcements</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* Tabs */}
      <Tabs
        value={selectedTab}
        onChange={(e, newValue) => setSelectedTab(newValue)}
        sx={{ mb: 3 }}
      >
        {tabLabels.map((tab, index) => (
          <Tab
            key={tab.value}
            label={
              <Badge
                badgeContent={
                  tab.value === 'all' 
                    ? discussions.length 
                    : discussions.filter(d => d.discussion_type === tab.value).length
                }
                color="primary"
              >
                {tab.label}
              </Badge>
            }
          />
        ))}
      </Tabs>

      {/* Discussions List */}
      {loading ? (
        <Box display="flex" justifyContent="center" p={4}>
          <Typography>Loading discussions...</Typography>
        </Box>
      ) : sortedDiscussions.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Forum sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="textSecondary" gutterBottom>
            No discussions found
          </Typography>
          <Typography variant="body2" color="textSecondary" paragraph>
            Be the first to start a discussion!
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setShowNewPostDialog(true)}
          >
            Start Discussion
          </Button>
        </Paper>
      ) : (
        <Box>
          {sortedDiscussions.map(discussion => renderDiscussionCard(discussion))}
        </Box>
      )}

      {/* New Post Dialog */}
      <Dialog
        open={showNewPostDialog}
        onClose={() => setShowNewPostDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Start New Discussion</DialogTitle>
        <DialogContent>
          <Box display="flex" flexDirection="column" gap={2} mt={1}>
            <FormControl fullWidth>
              <InputLabel>Discussion Type</InputLabel>
              <Select
                value={newPost.type}
                label="Discussion Type"
                onChange={(e) => setNewPost({ ...newPost, type: e.target.value })}
              >
                <MenuItem value="question">Question</MenuItem>
                <MenuItem value="tip">Tip & Trick</MenuItem>
                <MenuItem value="comment">General Comment</MenuItem>
              </Select>
            </FormControl>
            
            <TextField
              fullWidth
              label="Title"
              value={newPost.title}
              onChange={(e) => setNewPost({ ...newPost, title: e.target.value })}
              placeholder="Enter a descriptive title..."
            />
            
            <TextField
              fullWidth
              multiline
              rows={6}
              label="Content"
              value={newPost.content}
              onChange={(e) => setNewPost({ ...newPost, content: e.target.value })}
              placeholder="Describe your question or share your knowledge..."
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowNewPostDialog(false)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleCreatePost}
            disabled={!newPost.title.trim() || !newPost.content.trim()}
          >
            Post Discussion
          </Button>
        </DialogActions>
      </Dialog>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
      >
        <MenuItem onClick={() => setAnchorEl(null)}>
          <Star sx={{ mr: 1 }} />
          Bookmark
        </MenuItem>
        <MenuItem onClick={() => setAnchorEl(null)}>
          <Flag sx={{ mr: 1 }} />
          Report
        </MenuItem>
        {selectedPost?.user_id === user.id && (
          <>
            <MenuItem onClick={() => setAnchorEl(null)}>
              <Edit sx={{ mr: 1 }} />
              Edit
            </MenuItem>
            <MenuItem onClick={() => setAnchorEl(null)}>
              <Delete sx={{ mr: 1 }} />
              Delete
            </MenuItem>
          </>
        )}
      </Menu>
    </Box>
  );
};

export default DiscussionForum;
