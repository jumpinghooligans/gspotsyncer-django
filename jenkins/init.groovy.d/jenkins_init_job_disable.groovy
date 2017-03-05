import hudson.model.*
import hudson.triggers.*

// Disable jobs if we're in a DEV enviroment
def env = System.getenv("APP_ENV")
  
if (env == "DEV") {
  disableTimerTrigger(Hudson.instance.items)
} else {
  println('APP_ENV ' + env + ' != DEV')
}

def disableTimerTrigger(items) {
  for (item in items) {
    if (item.class.canonicalName == 'com.cloudbees.hudson.plugins.folder.Folder') {
        disableTimerTrigger(((com.cloudbees.hudson.plugins.folder.Folder) item).getItems())
    } else if (item.class.canonicalName != 'org.jenkinsci.plugins.workflow.job.WorkflowJob') {
      
      item.triggers.each{ descriptor, trigger ->
        if(trigger instanceof TimerTrigger) {
          println("--- Timer Trigger found for " + item.name + " ---")
          item.removeTrigger descriptor
          item.save()
        }
      }
    }
  }
}