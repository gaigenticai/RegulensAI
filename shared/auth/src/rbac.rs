//! Role-Based Access Control (RBAC) implementation

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use uuid::Uuid;

use regulateai_errors::RegulateAIError;

/// Permission structure
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Permission {
    /// Permission name (e.g., "users:read", "transactions:write")
    pub name: String,
    
    /// Resource type this permission applies to
    pub resource: String,
    
    /// Action allowed on the resource
    pub action: String,
    
    /// Optional conditions for the permission
    pub conditions: Option<HashMap<String, serde_json::Value>>,
}

impl Permission {
    /// Create a new permission
    pub fn new(resource: &str, action: &str) -> Self {
        Self {
            name: format!("{}:{}", resource, action),
            resource: resource.to_string(),
            action: action.to_string(),
            conditions: None,
        }
    }

    /// Create a permission with conditions
    pub fn with_conditions(resource: &str, action: &str, conditions: HashMap<String, serde_json::Value>) -> Self {
        Self {
            name: format!("{}:{}", resource, action),
            resource: resource.to_string(),
            action: action.to_string(),
            conditions: Some(conditions),
        }
    }

    /// Check if this permission matches a required permission
    pub fn matches(&self, required: &Permission) -> bool {
        // Wildcard permissions
        if self.name == "*" || self.resource == "*" || self.action == "*" {
            return true;
        }

        // Exact match
        if self.resource == required.resource && self.action == required.action {
            return self.check_conditions(required);
        }

        // Resource wildcard (e.g., "users:*" matches "users:read")
        if self.action == "*" && self.resource == required.resource {
            return self.check_conditions(required);
        }

        false
    }

    /// Check if conditions are satisfied
    fn check_conditions(&self, required: &Permission) -> bool {
        match (&self.conditions, &required.conditions) {
            (None, _) => true, // No conditions means permission is granted
            (Some(_), None) => true, // Required has no conditions, granted has conditions
            (Some(granted), Some(required)) => {
                // All required conditions must be satisfied by granted conditions
                required.iter().all(|(key, value)| {
                    granted.get(key).map_or(false, |granted_value| {
                        self.value_matches(granted_value, value)
                    })
                })
            }
        }
    }

    /// Check if a granted value matches a required value
    fn value_matches(&self, granted: &serde_json::Value, required: &serde_json::Value) -> bool {
        match (granted, required) {
            // Exact match
            (a, b) if a == b => true,
            
            // Array contains value
            (serde_json::Value::Array(granted_array), required_value) => {
                granted_array.contains(required_value)
            }
            
            // String wildcard matching
            (serde_json::Value::String(granted_str), serde_json::Value::String(required_str)) => {
                granted_str == "*" || granted_str == required_str
            }
            
            _ => false,
        }
    }
}

/// Role structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Role {
    pub id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub permissions: HashSet<Permission>,
    pub is_system_role: bool,
    pub parent_roles: HashSet<Uuid>,
}

impl Role {
    /// Create a new role
    pub fn new(name: &str, description: Option<String>) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: name.to_string(),
            description,
            permissions: HashSet::new(),
            is_system_role: false,
            parent_roles: HashSet::new(),
        }
    }

    /// Create a system role
    pub fn system_role(name: &str, description: Option<String>) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: name.to_string(),
            description,
            permissions: HashSet::new(),
            is_system_role: true,
            parent_roles: HashSet::new(),
        }
    }

    /// Add a permission to the role
    pub fn add_permission(&mut self, permission: Permission) {
        self.permissions.insert(permission);
    }

    /// Remove a permission from the role
    pub fn remove_permission(&mut self, permission: &Permission) {
        self.permissions.remove(permission);
    }

    /// Add a parent role
    pub fn add_parent_role(&mut self, parent_id: Uuid) {
        self.parent_roles.insert(parent_id);
    }

    /// Check if role has a specific permission
    pub fn has_permission(&self, required_permission: &Permission) -> bool {
        self.permissions.iter().any(|p| p.matches(required_permission))
    }
}

/// RBAC manager for handling roles and permissions
pub struct RbacManager {
    roles: HashMap<Uuid, Role>,
    user_roles: HashMap<Uuid, HashSet<Uuid>>,
}

impl RbacManager {
    /// Create a new RBAC manager
    pub fn new() -> Self {
        Self {
            roles: HashMap::new(),
            user_roles: HashMap::new(),
        }
    }

    /// Add a role to the system
    pub fn add_role(&mut self, role: Role) -> Result<(), RegulateAIError> {
        if self.roles.contains_key(&role.id) {
            return Err(RegulateAIError::AlreadyExists {
                resource_type: "Role".to_string(),
                identifier: role.id.to_string(),
                code: "ROLE_ALREADY_EXISTS".to_string(),
            });
        }

        self.roles.insert(role.id, role);
        Ok(())
    }

    /// Get a role by ID
    pub fn get_role(&self, role_id: &Uuid) -> Option<&Role> {
        self.roles.get(role_id)
    }

    /// Get a role by name
    pub fn get_role_by_name(&self, name: &str) -> Option<&Role> {
        self.roles.values().find(|role| role.name == name)
    }

    /// Assign a role to a user
    pub fn assign_role_to_user(&mut self, user_id: Uuid, role_id: Uuid) -> Result<(), RegulateAIError> {
        if !self.roles.contains_key(&role_id) {
            return Err(RegulateAIError::NotFound {
                resource_type: "Role".to_string(),
                resource_id: role_id.to_string(),
                code: "ROLE_NOT_FOUND".to_string(),
            });
        }

        self.user_roles.entry(user_id).or_insert_with(HashSet::new).insert(role_id);
        Ok(())
    }

    /// Remove a role from a user
    pub fn remove_role_from_user(&mut self, user_id: Uuid, role_id: Uuid) -> Result<(), RegulateAIError> {
        if let Some(user_role_set) = self.user_roles.get_mut(&user_id) {
            user_role_set.remove(&role_id);
            if user_role_set.is_empty() {
                self.user_roles.remove(&user_id);
            }
        }
        Ok(())
    }

    /// Get all roles for a user (including inherited roles)
    pub fn get_user_roles(&self, user_id: &Uuid) -> Vec<&Role> {
        let mut all_roles = HashSet::new();
        
        if let Some(direct_roles) = self.user_roles.get(user_id) {
            for role_id in direct_roles {
                self.collect_roles_recursive(role_id, &mut all_roles);
            }
        }

        all_roles.into_iter().filter_map(|id| self.roles.get(&id)).collect()
    }

    /// Recursively collect roles including parent roles
    fn collect_roles_recursive(&self, role_id: &Uuid, collected: &mut HashSet<Uuid>) {
        if collected.contains(role_id) {
            return; // Prevent infinite recursion
        }

        collected.insert(*role_id);

        if let Some(role) = self.roles.get(role_id) {
            for parent_id in &role.parent_roles {
                self.collect_roles_recursive(parent_id, collected);
            }
        }
    }

    /// Get all permissions for a user
    pub fn get_user_permissions(&self, user_id: &Uuid) -> HashSet<Permission> {
        let mut permissions = HashSet::new();
        
        for role in self.get_user_roles(user_id) {
            permissions.extend(role.permissions.clone());
        }

        permissions
    }

    /// Check if a user has a specific permission
    pub fn user_has_permission(&self, user_id: &Uuid, required_permission: &Permission) -> bool {
        let user_permissions = self.get_user_permissions(user_id);
        user_permissions.iter().any(|p| p.matches(required_permission))
    }

    /// Check if a user has a specific role
    pub fn user_has_role(&self, user_id: &Uuid, role_name: &str) -> bool {
        self.get_user_roles(user_id).iter().any(|role| role.name == role_name)
    }

    /// Check if a user has any of the specified roles
    pub fn user_has_any_role(&self, user_id: &Uuid, role_names: &[&str]) -> bool {
        let user_roles = self.get_user_roles(user_id);
        role_names.iter().any(|role_name| {
            user_roles.iter().any(|role| role.name == *role_name)
        })
    }

    /// Get all users with a specific role
    pub fn get_users_with_role(&self, role_id: &Uuid) -> Vec<Uuid> {
        self.user_roles
            .iter()
            .filter(|(_, roles)| roles.contains(role_id))
            .map(|(user_id, _)| *user_id)
            .collect()
    }

    /// Create default system roles
    pub fn create_default_roles(&mut self) -> Result<(), RegulateAIError> {
        // Super Admin role
        let mut super_admin = Role::system_role("super_admin", Some("Super Administrator with full system access".to_string()));
        super_admin.add_permission(Permission::new("*", "*"));
        self.add_role(super_admin)?;

        // Admin role
        let mut admin = Role::system_role("admin", Some("System Administrator".to_string()));
        admin.add_permission(Permission::new("*", "read"));
        admin.add_permission(Permission::new("*", "write"));
        admin.add_permission(Permission::new("*", "delete"));
        admin.add_permission(Permission::new("system", "*"));
        self.add_role(admin)?;

        // Compliance Officer role
        let mut compliance_officer = Role::system_role("compliance_officer", Some("Compliance Officer".to_string()));
        compliance_officer.add_permission(Permission::new("policies", "*"));
        compliance_officer.add_permission(Permission::new("controls", "*"));
        compliance_officer.add_permission(Permission::new("audits", "*"));
        compliance_officer.add_permission(Permission::new("reports", "*"));
        self.add_role(compliance_officer)?;

        // Risk Manager role
        let mut risk_manager = Role::system_role("risk_manager", Some("Risk Manager".to_string()));
        risk_manager.add_permission(Permission::new("risk", "*"));
        risk_manager.add_permission(Permission::new("assessments", "*"));
        risk_manager.add_permission(Permission::new("kris", "*"));
        risk_manager.add_permission(Permission::new("stress_tests", "*"));
        self.add_role(risk_manager)?;

        // Analyst role
        let mut analyst = Role::system_role("analyst", Some("Analyst".to_string()));
        analyst.add_permission(Permission::new("*", "read"));
        analyst.add_permission(Permission::new("reports", "write"));
        analyst.add_permission(Permission::new("analysis", "*"));
        self.add_role(analyst)?;

        // Auditor role
        let mut auditor = Role::system_role("auditor", Some("Auditor".to_string()));
        auditor.add_permission(Permission::new("*", "read"));
        auditor.add_permission(Permission::new("audits", "write"));
        auditor.add_permission(Permission::new("audit_logs", "*"));
        self.add_role(auditor)?;

        // User role
        let mut user = Role::system_role("user", Some("Standard User".to_string()));
        user.add_permission(Permission::new("dashboard", "read"));
        user.add_permission(Permission::new("profile", "*"));
        self.add_role(user)?;

        // Read-only role
        let mut readonly = Role::system_role("readonly", Some("Read-only User".to_string()));
        readonly.add_permission(Permission::new("*", "read"));
        self.add_role(readonly)?;

        Ok(())
    }
}

impl Default for RbacManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_permission_matching() {
        let wildcard_perm = Permission::new("*", "*");
        let specific_perm = Permission::new("users", "read");
        let resource_wildcard = Permission::new("users", "*");

        assert!(wildcard_perm.matches(&specific_perm));
        assert!(resource_wildcard.matches(&specific_perm));
        assert!(specific_perm.matches(&specific_perm));
        assert!(!specific_perm.matches(&Permission::new("users", "write")));
    }

    #[test]
    fn test_permission_with_conditions() {
        let mut conditions = HashMap::new();
        conditions.insert("organization_id".to_string(), serde_json::Value::String("org123".to_string()));
        
        let conditional_perm = Permission::with_conditions("users", "read", conditions.clone());
        let required_perm = Permission::with_conditions("users", "read", conditions);
        
        assert!(conditional_perm.matches(&required_perm));
    }

    #[test]
    fn test_role_creation_and_permissions() {
        let mut role = Role::new("test_role", Some("Test Role".to_string()));
        let permission = Permission::new("users", "read");
        
        role.add_permission(permission.clone());
        assert!(role.has_permission(&permission));
        
        role.remove_permission(&permission);
        assert!(!role.has_permission(&permission));
    }

    #[test]
    fn test_rbac_manager() {
        let mut rbac = RbacManager::new();
        
        // Create and add a role
        let mut role = Role::new("test_role", None);
        role.add_permission(Permission::new("users", "read"));
        let role_id = role.id;
        rbac.add_role(role).unwrap();
        
        // Assign role to user
        let user_id = Uuid::new_v4();
        rbac.assign_role_to_user(user_id, role_id).unwrap();
        
        // Check permissions
        let permission = Permission::new("users", "read");
        assert!(rbac.user_has_permission(&user_id, &permission));
        
        let no_permission = Permission::new("users", "write");
        assert!(!rbac.user_has_permission(&user_id, &no_permission));
    }

    #[test]
    fn test_role_inheritance() {
        let mut rbac = RbacManager::new();
        
        // Create parent role
        let mut parent_role = Role::new("parent_role", None);
        parent_role.add_permission(Permission::new("users", "read"));
        let parent_id = parent_role.id;
        rbac.add_role(parent_role).unwrap();
        
        // Create child role that inherits from parent
        let mut child_role = Role::new("child_role", None);
        child_role.add_permission(Permission::new("users", "write"));
        child_role.add_parent_role(parent_id);
        let child_id = child_role.id;
        rbac.add_role(child_role).unwrap();
        
        // Assign child role to user
        let user_id = Uuid::new_v4();
        rbac.assign_role_to_user(user_id, child_id).unwrap();
        
        // User should have both parent and child permissions
        assert!(rbac.user_has_permission(&user_id, &Permission::new("users", "read")));
        assert!(rbac.user_has_permission(&user_id, &Permission::new("users", "write")));
    }

    #[test]
    fn test_default_roles_creation() {
        let mut rbac = RbacManager::new();
        rbac.create_default_roles().unwrap();
        
        // Check that default roles exist
        assert!(rbac.get_role_by_name("super_admin").is_some());
        assert!(rbac.get_role_by_name("admin").is_some());
        assert!(rbac.get_role_by_name("compliance_officer").is_some());
        assert!(rbac.get_role_by_name("risk_manager").is_some());
        assert!(rbac.get_role_by_name("analyst").is_some());
        assert!(rbac.get_role_by_name("auditor").is_some());
        assert!(rbac.get_role_by_name("user").is_some());
        assert!(rbac.get_role_by_name("readonly").is_some());
        
        // Test super admin has wildcard permissions
        let super_admin = rbac.get_role_by_name("super_admin").unwrap();
        assert!(super_admin.has_permission(&Permission::new("anything", "anything")));
    }
}
