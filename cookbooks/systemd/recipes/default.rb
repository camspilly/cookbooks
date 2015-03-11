if gentoo?
  if root?
    package "sys-apps/systemd"

    include_recipe "systemd::cleanup"

    # by default, boot into multi-user.target
    service "#{node[:systemd][:target]}.target" do
      action :enable
      provider Chef::Provider::Service::Systemd
    end

    template "/etc/systemd/system.conf" do
      source "system.conf"
      owner "root"
      group "root"
      mode "0644"
    end

    cookbook_file "/usr/lib/tmpfiles.d/etc.conf" do
      source "etc.conf"
      owner "root"
      group "root"
      mode "0644"
      notifies :restart, "service[systemd-tmpfiles-setup.service]"
    end

    service "systemd-tmpfiles-setup.service" do
      action [:enable, :start]
      provider Chef::Provider::Service::Systemd
      only_if { systemd_running? }
    end

    # journal
    systemd_unit "systemd-journald.socket"

    service "systemd-journald.service" do
      action :nothing
      provider Chef::Provider::Service::Systemd
      only_if { systemd_running? }
    end

    template "/etc/systemd/journald.conf" do
      source "journald.conf"
      owner "root"
      group "root"
      mode "0644"
      notifies :restart, "service[systemd-journald.service]"
    end

    # networking
    file "/etc/hostname" do
      content "#{node[:hostname]}\n"
      owner "root"
      group "root"
      mode "0644"
    end

    service "sshd.service" do
      action :enable
      provider Chef::Provider::Service::Systemd
    end

    # modules
    file "/etc/modules-load.d/dummy.conf" do
      owner "root"
      group "root"
      mode "0644"
    end

    service "systemd-modules-load.service" do
      action :nothing # just a callback
    end

    # user session support
    systemd_unit "systemd-stop-user-sessions.service"
    systemd_unit "user-session@.service" do
      template true
    end

    service "systemd-stop-user-sessions.service" do
      action :enable
      provider Chef::Provider::Service::Systemd
    end
  end
end

if nagios_client?
  nagios_plugin "check_systemd"
  nagios_plugin "check_systemd_user"

  sudo_rule "nagios-systemd-active" do
    user "nagios"
    runas "ALL"
    command "NOPASSWD: /bin/env XDG_RUNTIME_DIR=/run/user/* systemctl --user is-active *"
  end

  sudo_rule "nagios-systemd-status" do
    user "nagios"
    runas "ALL"
    command "NOPASSWD: /bin/env XDG_RUNTIME_DIR=/run/user/* systemctl --user status *"
  end

  nrpe_command "check_systemd" do
    command "/usr/lib/nagios/plugins/check_systemd"
  end

  nagios_service "SYSTEMD" do
    check_command "check_nrpe!check_systemd"
    servicegroups "system"
    env [:staging, :testing, :development]
    register systemd_running? ? "1" : "0"
  end
end
