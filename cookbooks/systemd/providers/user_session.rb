include ChefUtils::Account

action :enable do
  user = get_user(new_resource.name)

  directory "#{user[:dir]}/.config/systemd/user" do
    owner user[:name]
    group user[:group][:name]
    mode "0755"
    recursive true
  end

  service "user-session@#{user[:name]}" do
    action [:enable, :start]
    only_if { systemd_running? }
  end

  execute "systemd-reload-#{user[:name]}" do
    command %{su -l -c 'env XDG_RUNTIME_DIR="/run/user/#{user[:uid]}" systemctl --user daemon-reload' #{user[:name]}}
    action :nothing
    only_if { systemd_running? }
  end

  systemd_user_unit "#{user[:name]}-dbus.socket" do
    unit "dbus.socket"
    user user[:name]
    cookbook "systemd"
  end

  systemd_user_unit "#{user[:name]}-dbus.service" do
    unit "dbus.service"
    user user[:name]
    cookbook "systemd"
    action [:create, :enable, :start]
  end
end

action :disable do
  user = get_user(new_resource.name)

  service "user-session@#{user[:name]}" do
    action [:disable, :stop]
    only_if { systemd_running? }
  end
end